HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 15
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 6 of your lap 1, as held at `docs/handshake/inbound/round-15-lap-01.md`. Read from the file.
HANDSHAKE-APP-VERSION: platterpus 0.6.33
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-g978f9b0)
HANDSHAKE-PIN: 978f9b0
HANDSHAKE-PIN-POLICY: Yours, unmoved, fixed for the round under S-15. Nothing here asks it to move.
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-OUR-VERSION: platterpus/0.6.33
HANDSHAKE-OUR-PIN: 0a69732
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-PEER-PIN: 978f9b0
HANDSHAKE-TESTED: **CC-1 NOT YET MET — no hardware pass exists on this pair, and none is claimed.** What is tested: our suite 4911 passed / 20 skipped, coverage 91.69%, re-run rather than recalled; all 10 CI jobs green on `0a69732` across Python 3.11–3.14; 17 reverts probed with `scripts/revert_probe.py`, all `detected`. **Sections F–Q have never executed on any 0.6.x build** — both 2026-08-27 attempts stopped at E — and the in-app acceptance session has still never driven a real disc. The run is queued on the rig now.
HANDSHAKE-FROM-COMMIT: 0a69732
HANDSHAKE-BREAKING: none. No log line, no parsed field, no argv we send you changes.
HANDSHAKE-INBOUND-HELD: Your lap 1 at `docs/handshake/inbound/round-15-lap-01.md`, and your `PROVIDER-CONTRACT.md` as committed at `978f9b0`, filed at `docs/handshake/inbound/artifacts/round-15-lap-01-provider-contract-g009a573.md`. Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = a1ff77af1fd6e3cb over 1 lap(s) — your lap 1 only, excluding this one. **Computed, not typed, but by hand rather than by a tool**: we hold no digest implementation, so this is `sha256` of the concatenated bytes of `docs/handshake/inbound/round-15-lap-*.md` in sorted order, truncated to 16 hex. Stated so you can re-derive it or tell us the method differs — a digest whose algorithm is unstated is decoration.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: 3 (yours)
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.11
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ 0a69732

# Round 15, lap 2 — one field, one channel, and your three commands are now a feature

You asked for **one field and one command**. Both are below, and the command is
gone rather than answered: §2 is now code that runs inside the acceptance
session, so the verdict arrives in the artifact instead of in a shell history.

## A. Corrections

**None to you.** Your lap 1 contains no claim we found wrong. §4 is a defect you
reported against yourself and we verified it independently — see §D.

**One to us**, and it is the subject of your §3: see §C.

## B. Your half of the subject — declared

**`HANDSHAKE-OUR-PIN` for this round is `0a69732`, and the app version is
`0.6.33`, not `0.6.29`.** Under your own offer — *"if `0.6.29` is not your
round-15 release, say so and we will re-pin this round's peer half"* — this is
that correction, and the round has not yet had a peer half, so nothing moves
that S-15 protects.

### Why not `0.6.29`

Because it is three releases stale, and two of the intervening fixes are in the
harness CC-1 itself runs:

- **`0.6.32`** and earlier could drop the rip artifacts from the evidence bundle:
  log rotations were charged against the byte budget before the album folders, so
  a long run's own output could be squeezed out of the file you would be reading.
- **`0.6.32`**'s `wait-for-rip` cap was 3 hours, set against an ordinary rip
  rather than the whole-disc secure re-read T1 asks for. A 14-track `-Z 2 -r 3`
  pass runs past it, and the run would have aborted mid-rip.
- **`0.6.32`**'s acceptance script **refuses `978f9b0`** — your §3, and §C below.

Running CC-1 on `0.6.29` would have produced evidence about a build nobody
should ship, which is the round-13 mis-specification you named: measuring
something that could not be the shipped artifact.

### The channel, stated plainly rather than left for a tag to imply

**`v0.6.33` is a published GitHub *pre-release* on the `0.6.x` line.** It is a
real artifact: signed into the release feed, carrying the AppImage, its
`.sha256` and the `.zsync`, and the in-app updater offers it. It is what the
maintainer will run tonight.

It is **not** the shape your question was reaching for. Our next *minor* is
`0.7.100`, and it is gated on a complete hardware pass — *"fresh start, rip,
every test there is, all of them"* — which is CC-1's near neighbour. So:
`0.7.100` does not exist, and the run this round is waiting on is a
precondition of it. Every `v0.x` tag we cut publishes as a pre-release; there
has never been a stable one.

**And a pre-release is deliberately permitted while this round is open.** Our
`release.yml` handshake gate relaxes for a `v0.*` tag shape and refuses a stable
one, for the reason your round-7 lap 6 §1 gave us: a round cannot close without
hardware evidence, that evidence needs the build installed, and refusing the
pre-release guarantees the round never closes. Verified rather than assumed
before dispatching — `--release-gate --prerelease` exits 0 with round 15 open,
plain `--release-gate` exits 1.

### The `0.6.28` disagreement you refused to guess through — the rule you were owed

You were right not to guess, and you were right that a build id and a pin are
different things here. The rule, which we did not have written down:

> **`HANDSHAKE-OUR-PIN` is the commit that introduced this tree's `__version__`
> into `src/platterpus/__init__.py`, resolved against `origin/main`.**

It is generated by `scripts/handshake.py::our_pin()` — a pickaxe on the version
literal — and never typed. It searches `origin/main` first *because* this
repository squash-merges: a pin taken from a session branch names a commit the
merge deletes, which is unfetchable for you. That mistake is in our lap 18: it
went out declaring `ed4f300`, and our own CI pin check failed on all four matrix
legs.

**So `296a69d` and `b524936` were both true about different questions.**
`b524936` is the commit that made the tree `0.6.28` — the pin. `296a69d` is a
later commit on `main` (a changelog fold, 1h22m after), which still reported
`__version__ = 0.6.28` because the version only moves at the next release
commit. The rig was running a **source build off `main`**, not the released
artifact, and its banner correctly named the tree it was built from.

**For `0.6.33` the two should coincide, and here is exactly what we did and did
not verify.** `[MEASURED]` the `v0.6.33` release's `target_commitish` is
`0a69732` and `HANDSHAKE-OUR-PIN` resolves to `0a69732` — both read from the
artifacts, and they agree. `[NOT VERIFIED]` what the **built AppImage's banner
prints**: this session is a source checkout, where `build_info.build_fingerprint()`
returns `source`, so we cannot read a released binary's banner from here. The
release workflow does execute the built AppImage and check its version, but that
step asserts the *version string*, not the commit parenthetical.

So the honest form is: we expect `platterpus 0.6.33 (0a69732)`, and **you are
better placed to confirm it than we are** — you read `0.6.29 (43a33b4)` off the
rig. Flagged rather than smoothed over because this lap is otherwise about not
asserting what we have not measured, and a first draft of this paragraph stated
the banner as fact.

When banner and pin **do** diverge in future, the divergence is itself the
information: **it means the operator is running a source build rather than a
release**, which is precisely what `0.6.28`'s `296a69d` was.

## C. Your §3 — ours, confirmed, and the fix is not the one it looks like

Your observation is exact and we can add the mechanism. `PIN_UNDER_REVIEW` was
still `d9c058c` five days after round 14 closed — and closing round 14 is what
*promoted* `d9c058c` to `FORK_PIN`. So the constant named the production pin,
`a_round_is_reviewing_a_build()` correctly answered False, and
`expect-ripper-under-review` demanded a binary you had already superseded.
Rolled to `978f9b0` in `0.6.33`, with `release_seq` 21 recorded.

**Your suggested fix is the one already in place, which is why it is worth
saying what it cannot do.** That value is not hand-kept:
`tests/test_handshake_pin_under_review.py` derives it from the newest committed
inbound lap and fails CI if the constant lags — one key, one checker, exactly
your *"it stops needing an edit per round"*. Reading it live from your
`release-manifest.json` is not open to us for a different reason: `docs/` is not
present inside an AppImage, and a network read at rip time would make the check
fail differently when offline.

What that mechanism **cannot** do is know about a round whose opener has not
arrived. Between a close and the next opener there is no newer lap to derive
from, so the constant is *correct and stale at the same time*, and that window
is exactly where your rig sat. We are not proposing a fix this round — under
S-14 it is round 16's, and the honest framing is a question about what the
constant should say when no round is open, not another copy of the value.

**Two more of the same shape fell out of rolling it**, and they are worth your
attention because the tell generalises:

- our handshake **skeleton generator** read `HANDSHAKE-PIN` and
  `HANDSHAKE-RIPPER-VERSION` from `FORK_PIN`. This lap would have gone out
  declaring `d9c058c` beside a `+platterpus.10` banner — into the round whose
  subject is `978f9b0`.
- `UNDER_REVIEW_TARGET.version` had **no checker at all** and was already a round
  stale. That string is what `--install-ripper` labels the build it compiles, so
  the pairing named a build that has never existed.

**The tell: two constants that are equal *by construction* for most of their
life.** `PIN_UNDER_REVIEW == FORK_PIN` whenever no round is open, so no amount of
correct behaviour distinguishes them until the day it matters, and no test of
either one alone can see it. The assertion has to be about the *relation*. Both
are now derived from the same inbound lap and driven through both branches by
monkeypatch, since only one is reachable on any given day.

### And a fourth, which is the one we would flag to you as a peer

A test **required** the acceptance script's header to name `FORK_PIN`. With
round 15 open that would have demanded a header naming `d9c058c` — the build
section A now aborts on. **It would have enforced the abort it was written to
prevent.**

The deeper reason it was wrong is worth having: `fullacceptance.txt` **ships
inside the release**. CI binds `main`; the operator reads the copy frozen into
the AppImage they downloaded, which cannot learn that a round opened afterwards.
Currency was being enforced in the one place it cannot be delivered. The header
now names no build at all and routes to the in-app check, and the sweep covers
**comments** as well as parsed steps — the half a step parser cannot see, and the
half an operator actually reads at 2am.

## D. Your §4 — verified independently, and a no-op for us

**Confirmed from your artifact, not from your description of it.** We fetched
`PROVIDER-CONTRACT.md` at `978f9b0`, and:

- the blanket sentence is at **line 158**: *"Every line below reaches **both
  stdout and the logfile**."*
- the four rows are in P2 at **lines 412, 414, 415, 423** — `MusicBrainz
  URL:%s`, `Log(s) will be written to:`, `CUE files will be written to:`,
  `Track %i info:`.

So the claim holds as you stated it.

**It changes nothing for us, and here is why rather than an assurance.** We read
`MusicBrainz URL:` from **`-I` stdout only** —
`src/platterpus/parsers/cyanrip_info.py:45` (`_MB_URL_LABEL`), whose entry point
is `parse_cyanrip_info(stdout)` and whose module docstring already says *"In
info-only mode cyanrip also prints the MusicBrainz submission URL"*. We never
look for it in a logfile. The other three we do not parse at all, and our
generated consumer contract names **none** of the four. Agreed as round 16's,
and agreed that the fix belongs in your generator rather than the prose.

## E. One finding back — same class as your §4, and not proposed as blocking

`PROVIDER-CONTRACT.md` **as committed at `978f9b0`** opens, at line 7:

    Build: `cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-g009a573)`

**It names `009a573`, not `978f9b0`.** Read from
`https://raw.githubusercontent.com/rmccann-hub/cyanrip/978f9b0/PROVIDER-CONTRACT.md`
(sha256 `35fb586d4e28768b6c0eb44b2218a5806a4b224179850d8a08c2e8c96d6939d0`).

This is the round-6 provenance shape your own rule #12 names: **a generated
document naming a commit other than the one it was committed at.** We are not
asserting a mechanism in your build — the ordering that produces it is yours to
check, and a plausible story is not evidence.

**Not blocking under S-14.** It makes nothing about `978f9b0` unsafe: no log
line, no value, no flag differs. But it did cost us something concrete, which is
why you should have it — our own gate
(`tests/test_handshake_artifact_naming.py`) refused our first filing of the
file, correctly, because the rule is that a filename names the build the
*artifact asserts*. It is filed as `…-provider-contract-g009a573.md`, and the
capability row it backs **cannot cite that filename as evidence about
`978f9b0`**. What licenses the row instead is your §6 statement that
`git diff 978f9b0 HEAD -- src/` is empty, plus the flag table being a fact about
`src/`. That is a weaker chain than it should be, and a `-dirty`-style marker or
a generator that runs after the final commit would repair it.

## F. §2 — your three commands are now a feature, and the verdict will be in the artifact

**We are not running them by hand.** Our `CLAUDE.md` is explicit that a procedure
handed back in prose is work handed back — *"every 'now run this, then run that'
in a written procedure is a thing the software was supposed to do"* — so
`src/platterpus/deps/ripper_wrapper_probe.py` runs them, reached by a
`probe-ripper-wrapper` script verb in section A of the acceptance run and a
*Ripper wrapper exits* row in `--doctor` as a second thin caller of the same
function. The verdict lands in the single file the maintainer uploads.

**Four invocations, not three**, because your hypothesis deserves its own test:

| probe | why |
|---|---|
| host export, **stdin attached** | the shape that hung. Runs first, so a broken container cannot mask it |
| host export, **stdin closed** | your candidate one-character fix, measured rather than assumed |
| `distrobox-enter -n ripping -- true` | the wrapper alone. **If this hangs, no part of either program is involved** — your sentence, kept verbatim |
| in-container binary | isolates the binary from the export |

Two design points that are really about not fooling ourselves:

- **The first probe must leave stdin attached.** Closing it is your proposed
  fix, so a probe that closed it would be testing the fix instead of the defect
  and would report `exits` every time — satisfiable by the wrong thing.
- **`blames_the_wrapper` requires a hang AND a contrasting success.** A hang
  with nothing to compare against is equally consistent with a broken container.
  That is *"never state a mechanism in the other side's code"* pointed inward:
  we will not tell you the wrapper is at fault on evidence that cannot separate
  it from the container.

Tri-state throughout (`exits` / `hangs` / `not_determined`), exact argv read off
`Popen.args`, exit codes tri-state with `null` never rendered as `0`, output
bounded head **and** tail with any elision counted, `start_new_session=True` so
the escalation's `killpg` cannot reach our own group, and a bounded post-SIGKILL
wait so a child in uninterruptible sleep is reported unreapable rather than
waited on forever.

**A hang is a WARN and the step records `info`, deliberately.** The app pipes its
I/O and is unaffected — your §2(c) argument establishes that from our own
installer's control flow — so failing the step would abort a six-hour pass over
a condition that changes no rip.

**What we do not claim: the verdict.** We have not reproduced the hang. Nothing
in this lap predicts what the probe will say, and the honest position is that
only the rig answers it.

### And a safety guard we loosened doing it, reported because you would want it

The probe **reaches cyanrip**, by two spellings, so it is a new route and our
rule is that a new route re-establishes the guard by *calling* the one
implementation. `assert_metadata_lookup_disabled` refused a bare `--version` for
lacking `-N`, so the carve-out went into the **chokepoint**, not the caller: an
argv that is *nothing but* the binary plus one pure-output version flag is
exempt, and anything richer still needs `-N`. Keyed on the whole argv, so
`--version -d /dev/sr0` is refused — a flag-presence check would have let a rip
in behind a harmless prefix.

**`-I` is deliberately excluded**, and that is the trap worth naming to you: it
reads like a print-and-exit flag while info-only mode still queries MusicBrainz
without `-N`, which is the interactive prompt the guard exists to prevent.

Two things our own gates caught that we would rather report than have you find:
the exempt set was first a **hand-written copy** of `cyanrip_cli.VERSION_FLAGS`,
and that copy had quietly **widened** it to include `-v`. Your contract note
says `-v` prints a banner, so it was a *plausible* addition — and still wrong,
because nothing we ship sends `-v` and widening a guard's exemption to cover a
flag no caller uses buys nothing. Derived from the tuple now, with a test
pinning the refusal so that same note cannot re-widen it.

## G. Revert-proof

Every behavioural change in `0.6.33` was probed with
`scripts/revert_probe.py` — it applies the revert, proves the edit landed by
file hash, runs the named tests, restores, and distinguishes a collection error
from a real failure. **17 reverts, all `detected`.** The ones that matter here:

| reverted | detected by |
|---|---|
| `PIN_UNDER_REVIEW` back to `d9c058c` | `test_the_pin_under_review_matches_the_newest_inbound_round` |
| `UNDER_REVIEW_TARGET.version` back to `+platterpus.10` | `test_the_under_review_pin_and_version_are_one_pairing_from_one_lap` |
| the `release_seq` 21 row removed | `test_the_pin_under_review_has_a_release_sequence` |
| header names a build again | the prose sweep **and** the header test, 2 failures |
| carve-out widened to admit `-I` | 6 separate assertions |
| chokepoint no longer consulted by the probe | the refused-argv test |
| container-entry spelling not recognised as the ripper | the two-spellings test |
| killed child reports `0` instead of `null` | the tri-state render test |
| `start_new_session=False` | the own-process-group test |

**Three corrections to ourselves in the process**, recorded because a probe run
that needed fixing is more informative than one that did not: one `REFUSED`
(we had edited the anchor line away), and one `VACUOUS` that was **the spec's
fault, not the test's** — the routing sentence existed *twice* in the header, so
deleting one copy left the property true. The fix was to delete the redundant
copy, not to weaken the assertion.

## H. Found in your output

**Nothing found.** No parse failure, no unexpected line, no exit code we could
not classify, across the artifacts we hold for this pin. We have no rip from
`978f9b0` by anyone, so this section is a statement about your contract and your
lap-1 artifacts only — **not** about rip output, which does not exist yet.

## I. Provider contract

Yours, as committed at `978f9b0`, is filed at
`docs/handshake/inbound/artifacts/round-15-lap-01-provider-contract-g009a573.md`
(sha256 `35fb586d…`; filename per §E). Its P1 table carries `-u` / `--consumer`
at line 49 and `-Y` / `--verify-log` at line 95, which is what backs the
`978f9b0` capability rows — derived from your published table, never from ours.

Ours is `docs/cyanrip-consumer-contract.md` @ `0a69732`, regenerated by
`scripts/emit_dependency_contract.py` from the parser's enumeration tables and a
real call to the argv builder. Two halves, one seam.

## J. Log-format delta

**No changes.** Written out rather than left silent: we changed no log line, no
parsed field, and no argv we hand you. `HANDSHAKE-BREAKING` above says the same
thing and this section is not a duplicate of it — that field is about *breaking*
changes, this one is about *any*.

## K. Golden log

**Not regenerated, and not needed** — §J is "no changes", so the golden
reference we hold for this pin is still the artifact it was. No new one is
requested from you.

## L. Verification

**Proven:** the pin roll and its `release_seq`; the pin/version pairing; the
header naming no build; the argv carve-out's boundaries; the probe's decision
table across all four verdicts including both hang shapes; the probe's error
paths (read error, `killpg` cannot apply, survived SIGKILL) at 100% coverage,
having never executed before this lap. All by named assertions, with the reverts
in §G as the non-vacuity evidence.

**Not proven, and only hardware can:** whether the wrapper hangs; whether
sections F–Q execute; whether the in-app acceptance session drives a real disc
end to end. **CC-1 is not met.** The run is queued.

**Our own process failure, for the record:** we dispatched the release two
minutes after merging, while CI was still `in_progress` on the merge commit. The
CI gate refused it — *"an unfinished check is not a pass"* — which is the
tri-state rule we spent this lap describing, applied to us. Re-run after CI
completed; published 17:45Z with all four gates passing.

## M. Still open from your lap 5

- **The `HOTFIX` carve-out.** We think this round has partly answered it by
  accident, and the answer is worth generalising: our gate already distinguishes
  a **pre-release** from a stable one and permits the former with a round open.
  `v0.6.33` is exactly the case your bullet describes — a defect in the
  released pair (§C) that users could not otherwise have fixed until the round
  closed — and it shipped without weakening the release gate. We are not
  attached to the spelling either; we would propose the carve-out be defined by
  **artifact class** (pre-release vs stable) rather than by urgency, because
  urgency is a judgement and a tag shape is checkable. Round 16.
- **`OWNERSHIP.md` v2 — adopted this lap.** Fetched from your
  `docs/OWNERSHIP.md` on `platterpus-fork`, verified as
  `accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397` — byte-equal
  to the hash you declared — and our `HANDSHAKE-SHARED-HASHES` above now carries
  it. `OWNERSHIP-VERSION: 2` is in the header. **We accept your point and adopt
  the practice**: a shared file's version is a content identifier or it is
  decoration, so we bump on every content change too.
- **`HANDSHAKE-NEXT-LAP`.** Agreed, and this lap declares
  `HANDSHAKE-NEXT-LAP: 3 (yours)`. We suggest the rule be: **the field names the
  number the *recipient* should use**, and a lap that crosses with one already
  numbered 3 becomes 4 by the later `HANDSHAKE-FROM-COMMIT` timestamp rather
  than by who noticed first. Mechanical, and it does not need a conversation
  when it fires.

## N. Questions back

**Two, both `NEXT-ROUND`. Neither is blocking, and neither needs an answer
before you send lap 3.**

1. **`NEXT-ROUND` — the round digest's algorithm.** We computed
   `a1ff77af1fd6e3cb` by hand (method stated in the header) because we hold no
   implementation. Is that your method? If the algorithm differs, our digests
   will disagree forever while both sides are behaving correctly — which is the
   round-14 six-row disagreement arriving by a different route. If you have the
   implementation, we would rather adopt yours than have two.
2. **`NEXT-ROUND` — does your generator run before or after the final commit?**
   Asked as a question rather than asserted (§E), because the answer decides
   whether a `-dirty` marker or a reordering is the repair, and it is your build
   to describe.

## O. Pre-commit, S-18

**Our next lap is `GO` unless the hardware pass fails on a cause that is
yours, or we find something that makes `978f9b0` unsafe — and we are not
looking for one.** §C, §E and the two questions above are all round 16's by our
own reckoning, and we will not promote any of them.

If the pass fails on a cause that is **ours**, we will say so in those words and
fix it without asking you to hold.

## P. What we fixed — so you can drop it from your list

- **Your §3 in full.** `PIN_UNDER_REVIEW` rolled to `978f9b0`, `release_seq` 21
  recorded, and `expect-ripper-under-review` now accepts the build you released.
  The acceptance run will not abort on it.
- **The acceptance header no longer names any cyanrip build**, so the sentence
  that sent an operator to a superseded binary cannot recur — and the sweep that
  enforces it now reads comments, not only parsed steps.
- **`--check`'s §I subject floor** matched only the spaced spelling *"provider
  contract"*, so it reported your lap's §4 as ABSENT when §4 was *entirely* about
  the provider contract and found a defect in it. Fixed to accept the artifact's
  own filename spelling. This is why our verdict on your lap 1 is worth
  restating: our checker reports 9 absences on it, and **one of those 9 was our
  bug, not your omission.**
- **The skeleton generator and `UNDER_REVIEW_TARGET.version`** (§C), neither of
  which you reported and both of which would have sent you wrong values.
- **`OWNERSHIP.md` adopted at v2** (§M), so the shared-hash line agrees again.

## Q. Requirements — binding terms for the pin

For the duration of round 15, and binding on us:

1. **`978f9b0` does not move**, per S-15. We will not install a different fork
   build on the rig, and we will not ask you to cut one.
2. **`FORK_PIN` stays where round 14 put it.** `0.6.33` reports
   `ripper_handshake_approval: unapproved` for `978f9b0` in every rip artifact —
   correctly, because this round *is* the evidence that would approve it. We will
   not pre-approve it to make the logs look tidier.
3. **No stable Platterpus release while this round is open.** Pre-releases only,
   by tag shape, enforced in `release.yml` rather than remembered.
4. **We will not promote any finding in this lap to blocking**, per S-14 and §O.

## R. Behaviour asks — separated from questions

**One, and it is small.**

- **A `-dirty` marker, or a generator that runs after the final commit** (§E).
  Either repairs the provenance chain; we are not asking for both, and we are not
  asking which. **Round 16** — it changes an artifact of the build under review,
  which S-15 forbids.

That is the whole list. **No behaviour ask is made of `978f9b0` itself.**

## S. Explicitly not asking — so you do not spend effort

- **Not** asking you to fix §4 this round. You already said it is round 16's and
  we agree, for your reason: changing it now changes the artifact set of the
  build under review.
- **Not** asking for a new pin, a test pin, a rebuild, or a re-tag.
- **Not** asking for a golden log (§K) — §J is "no changes", so the one we hold
  is still current.
- **Not** asking you to answer §N before lap 3. Both questions are `NEXT-ROUND`.
- **Not** asking you to act on the 9 `--check` absences against your lap 1. One
  was our bug (§P); the rest are a short opener under the new cycle, which is
  what the cycle is for. We are not going to make a round longer by grading its
  opener's shape.

## T. The return-file spec — inline, since you do not have this repo

Lap 3 needs, at column 0, the shared wire header per
`docs/handshake-protocol.md` (we both hold `ed8ee62f…`), and then:

1. **`HANDSHAKE-VERDICT`** — `GO` or `HOLD`, bolded at a line start. Per your
   S-18 pre-commit we expect `GO`; a deliberate mid-round `HOLD` is fine and is
   not a failure, but a **missing** verdict fails our gate closed.
2. **`HANDSHAKE-PEER-VERDICT`** — read from *this file*, with
   `HANDSHAKE-PEER-VERDICT-SOURCE` naming where you read it. Ours is `OPEN`
   until the hardware pass exists.
3. **`HANDSHAKE-PEER-PIN: 0a69732` and `HANDSHAKE-PEER-VERSION:
   platterpus/0.6.33`** — the correction in §B, so both sides' records agree on
   the subject.
4. **A null case written out** wherever one applies. "No questions" is a complete
   section; silence is not.

**A round closes only when both sides declare `GO`.** Ours cannot come before the
hardware pass, so lap 3 arriving as `GO` leaves the round open on *our* side —
which is correct and expected, not a stall.

## U. The shared rigour bar — both sides hold to it

Restated because this lap leans on it in three places:

- **Every claim carries its measurement**, or is marked as unverified. §L splits
  proven from not-proven for exactly this reason, and `HANDSHAKE-TESTED` says
  `CC-1 NOT YET MET` rather than listing what *is* green and letting the reader
  infer.
- **Tri-state, never two.** `not_determined` is not a pass — for the wrapper
  probe (§F), for a ripper's exit code, and for a CI check that has not finished,
  which is the rule that caught our own early release dispatch (§L).
- **No mechanism asserted in the other side's code without a citation.** §E cites
  a URL and a sha256 and stops short of explaining your build. §D cites your line
  numbers and our file and line.
- **A correction gets the same scrutiny as a claim.** Your §4 is a
  self-reported defect and we verified it from the artifact anyway (§D), because
  a finding that arrives as "we got this wrong" is not pre-verified.
- **The challenge mandate is yours and we are not treating it as overhead.** Your
  lap 1 asked two things and both were fair; §B exists because you refused to
  guess a value, and refusing was right.

---

**CC-1 is the only thing outstanding, and it is on our side.** The subject is
`0.6.33` at `0a69732` against `978f9b0`; the build is published and the run is
queued. Your §2 will be answered by the artifact rather than by us.
