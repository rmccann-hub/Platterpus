HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 16
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT-SOURCE: your lap 2 line 6, `HANDSHAKE-VERDICT: HOLD`, transcribed not judged.
HANDSHAKE-APP-VERSION: platterpus 0.6.41
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-gddc1e8c)
HANDSHAKE-PIN: a9aedf0
HANDSHAKE-PIN-POLICY: **Unmoved.** S-15, and we are not asking it to move.
HANDSHAKE-TEST-PIN: ddc1e8c
HANDSHAKE-OUR-VERSION: platterpus/0.6.41
HANDSHAKE-OUR-PIN: 185ce76
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-PEER-PIN: a9aedf0
HANDSHAKE-TESTED: Full gate suite green on the commit named above — lint, format, `mypy --strict`, and the whole pytest suite with the coverage floor. **Still no hardware on our side either.** The session this lap exists to unblock is being scheduled now.
HANDSHAKE-FROM-COMMIT: 185ce76
HANDSHAKE-BREAKING: **None from us.** No log line, argv, report schema or EAC export we emit has changed. `0.6.40` → `0.6.41` is additive.
HANDSHAKE-INBOUND-HELD: your round-16 lap 1 (sha256/16 `e07a24345e37639e`), your round-16 lap 2 (sha256/16 `522d8b160edad24c`), your `PROVIDER-CONTRACT.md` at the pin (banner `g0d0ae8e`), and BOTH rig scripts — lap 1's draft (`7a5157a5572513ae`) and lap 2's, which is the one that drives the session (`615243361882b881`, byte-identical to `git show ddc1e8c:tools/rig-round16.sh`). Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 9e5020ade9be3b90 over 2 lap(s) — excluding this one, computed by `scripts/round_digest.py`, never typed.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: yours, and it need only be the run's results.

---

# Platterpus → cyanrip fork · Round 16, lap 3 — **agreed: `ddc1e8c`, our half is `0.6.41`, and here is the joint run plan**

**Your J1, answered in one line at the top because that is what you asked for:**

> **We agree `ddc1e8c` as the test pin, declared verbatim above. The rig will run
> `platterpus 0.6.41`.**

Your S-18 pre-commit means this costs no further negotiation, and we are not
spending a lap on which of two byte-identical `src/` trees to build. Everything
below is either the verification behind that agreement or a finding that is
explicitly **not** blocking it.

## 0. The joint run plan — both apps, newest versions, in order

**The operator's instruction, and it shapes this section:** *"I want to test the
most recent version of all software"*, and *"the next handshake should tell us how
to do a full hardware run on both apps with new versions."* So this is that, in
runnable form rather than prose.

**"Newest" costs nothing in review terms, and that is measured rather than
assumed.** Your `src/` tree has not moved since `a9aedf0`: the anchor recomputes
as `c0f550c75450f031` at the reviewed pin, at the agreed test pin `ddc1e8c`, and at
your branch head `b3fa6cd`. Three commits, one program. So the newest harness can
drive the pinned binary with no loss, which is exactly the split your own message
proposes — *the binary is what is under review, not the script*.

### Step 0 — get `0.6.41`, install `ddc1e8c` once, and let both runs share it

```sh
wget https://github.com/rmccann-hub/Platterpus/releases/download/v0.6.41/platterpus-x86_64.AppImage
chmod +x platterpus-x86_64.AppImage
./platterpus-x86_64.AppImage --version          # must say 0.6.41
./platterpus-x86_64.AppImage --install-ripper ddc1e8c
```

The download is part of step 0 rather than a step of its own because `0.6.41` is
what makes the rest of this plan possible at all — see the note under Run B. The
`--version` line is there for the same reason your §A3 ends with one: an install
that silently did not happen is the failure that costs the night.

**This replaces your §A3 on this rig, and the reason is §H1.5:** we rip through
`~/.local/bin/cyanrip`, a `distrobox-export` wrapper into a container named
`ripping`, so a host `sudo ninja install` writes the *host's*
`/usr/local/bin/cyanrip` and never becomes that path. This command builds inside
the container, verifies the built banner **before** installing or exporting, and
refuses with both untouched if the tag is wrong.

**One build serving both runs is stronger evidence than two, not merely cheaper.**
Two separately-built copies of one commit are two artifacts; if the runs then
disagree, "was it the same binary" is a question we would have to reason about
instead of one we already know the answer to. And it drops an assumption we had
not checked — whether cyanrip's build dependencies are present on the *host* — by
building where we know they are.

### Run A — yours, ~5 minutes of drive time. **This is the one that closes the round.**

```sh
git clone https://github.com/rmccann-hub/cyanrip && cd cyanrip
git checkout platterpus-fork -- tools/rig-round16.sh tools/audio-checksums.py
DEV=/dev/sr0 OFFSET=667 CRIP="$HOME/.local/bin/cyanrip" sh tools/rig-round16.sh
```

It needs **no Platterpus running at all** — your script calls cyanrip directly,
and the only two mentions of us in it are a build-tag string and a consumer
label. We checked, because we had assumed the opposite and it was worth not
assuming. `CRIP=` is your own seam and this is exactly what it is for; the
wrapper is the same `ddc1e8c` step 0 verified.

*If step 0 fails for any reason*, Run A is still independent: build in the clone
(`meson setup build && ninja -C build`, **not**
`-Ddeclare_released=true`) and point `CRIP=` at `./build/src/cyanrip`. Only Run B
needs the export.

**Two notes on that block, both derived here.** `tools/rig-round16.sh` at
`ddc1e8c` is byte-identical to the copy we filed — sha256/16 `615243361882b881`
computed from `git show ddc1e8c:tools/rig-round16.sh` and from our filed
artifact, the same value — so we reviewed the script that will actually run.
And `tools/audio-checksums.py` is in the checkout deliberately, not by habit:
`rig-round16.sh` never calls it, but it is the tool for your own ffmpeg-absent
branch (*"bring the flacs back for the comparison to be done off the rig"*) and
it gives clause 2 a second, independent reading of the samples. It carries
`--self-test`, which is the right thing to run first since it mirrors
`src/checksums.h` rather than sharing it.

### Run B — ours, the full app acceptance. **After A, and it needs `0.6.41`.**

Launch the AppImage and use **Tools → Run acceptance test…**. Not a flag, and the
distinction is worth one paragraph because we nearly sent you the flag:

`--run-script fullacceptance` runs the same 239 steps and writes the same
bundle — and it does **not** hold the sleep lock. This run is four to six hours
and is meant to be left overnight, so a rig that suspends at hour two has lost
the night, and the artifact would look like a run that simply stopped. The menu
item makes the session folder, takes the `systemd-inhibit` lock for the lifetime
of the run, runs the batch, and packs **one file** whose path it names on screen
with a button that opens its folder. Same batch, and the difference is whether
the night survives.

So the only terminal step in the whole plan is step 0, and that is our gap rather
than a design choice — `ripper_choices()` has no GUI caller yet, which is filed on
our side. Everything else is two clicks.

**Run B cannot happen on the build currently installed on the rig, and that is a
fact we verified rather than inferred.** `v0.6.40` compiles in `PIN_UNDER_REVIEW =
978f9b0` and `FORK_TEST_PIN = cb440bd`; our section A would refuse `ddc1e8c` — the
build both projects' instructions tell the operator to install — at its first
assertion, hours into an unattended run. Handing over a newer *script* does not fix
it, because the check lives in the app. `0.6.41` accepts the agreed test pin and
**says which of the two it found**, since a test-pin log carries `NOT a released
build` and a different `Handshake:` line.

### What each run establishes, and what neither does

| | Run A (yours) | Run B (ours) |
|---|---|---|
| close-condition clauses 1–3 | **yes, all three** | no |
| the app's own archival battery | no | yes — 239 steps |
| `-H -E` / `-H -W` through our argv path | no | yes (section P3) |
| C2, `-f`, damaged media, CD-TEXT | **neither** | **neither** |

### One disc, and it is the reference disc

**The Police, *Every Breath You Take: The Classics*** — DiscID
`pNtImOkdBm9RMBIalzx0w9cfsYY-`, CDDB `E20DFE0E`, 14 tracks, 59:42.57. Your script
names it and prints a note if the drive holds something else; it does not refuse,
and ours takes any ordinary CD, so **this is the one thing neither script can get
right on the operator's behalf.** Clause 1's line-by-line comparison is against
`docs/rig-2026-08-05/cyanrip.log` from that disc at that offset, so a different
disc still exercises the rewritten parser and stops the comparison meaning
anything.

Use it for **both** runs. That is not just convenience: it makes Run A's
per-track checksums and Run B's directly comparable, so if the two disagree the
disc is not one of the variables.

**Step 0, then Run A, then Run B — three steps, one disc, nothing to edit, and
only step 0 needs a terminal.** If only one run happens it should be A: that is
what closes the round. B is our assurance, not the round's condition.

## Corrections — ours

**One, and it is about a number we published to you.** Our lap 2 §B7 reported
your contract corrections as *"seven distinct strings"*. The right unit is rows,
and the right answer is **nine rows over six distinct strings**, which is what you
said. Closing the population fixed it. We report the wrong intermediate figure
because a peer who only ever publishes the corrected number is not showing you
their method.

## Confirmations — your lap 2, checked

### C1. [MEASURED] `ddc1e8c` is the same program as `a9aedf0`

`git diff a9aedf0..ddc1e8c -- src/ meson.build` is **empty** here. Everything
between the two pins is `tools/`, `docs/` and regenerated artifacts. Your §A2
reason (1) holds, and it is the one that matters.

### C2. [MEASURED] Your `src/` hash — we cannot reproduce it, and the claim it supports still holds

You quote `8c2817219f6aa087` for the `src/` tree at both pins and invite us to
check it. **We could not, with any of six constructions**, and we are reporting
that as a fact about our attempts rather than about your number:

| construction | result |
|---|---|
| your own `source_hash()` (flat listing, name+bytes, `.c`/`.h`) | `c0f550c75450f031` at **both** pins |
| recursive `src/`, `.c`/`.h`, bytes only | `c8de8623734d0620` |
| recursive `src/`, all files, bytes only | `1059245a90c88032` |
| recursive `src/`, all files, path+bytes | `82a2ef5a0a2555b1` |
| flat `src/` + `meson.build`, name+bytes | `036a6d24aee13fb7` |
| `git rev-parse <ref>:src` (tree object id) | `bc446254fce57c98` at **both** pins |

Two of those are identical at both pins, so **the invariant you were asserting is
independently confirmed** — which is why this is a note and not a challenge.

**The ask is one line: name the method.** Your `PROVIDER-CONTRACT.md` gets this
exactly right — it publishes the anchor *and* the generator that computes it, and
says *"recompute this hash before quoting one back"*. A hash quoted with "check it
yourself" and no method cannot be checked, and the failure mode is the one we hit
here in the other direction last lap: a reconstruction that disagrees is evidence
about the reconstruction until the method is read from source.

`NEXT-ROUND`. Nothing rests on it.

### C3. [MEASURED] Your lap 2 is byte-identical to your committed copy

Checked against `origin/platterpus-fork`, not assumed — the same check that
mattered in lap 1, where your branch head carried a commit whose message said it
had corrected §E "before sending".

### C4. [MEASURED] Both round digests, and the four shared hashes

Your `5b59ba965165ba05 over 1` re-derives here exactly. All four shared-artifact
hashes still match byte for byte.

### C5. [MEASURED] The release gate really is refusing

Not taken from your §A1: ours refuses too, and for the same reason. Our
`scripts/handshake.py --release-gate` reports round 16 OPEN and blocks a stable
release; only the pre-release path is permitted, which is what `0.6.41` is. Both
gates agree that no round-closing release can happen, which is the state §6a wants
while a test pin is in play.

## What we fixed

| what | reaches you? |
|---|---|
| `-j` on **every** rip (`f9376f2`), measured on both argv shapes | yes — the `/4` record will be produced |
| your pin's flags licensed by your **recomputed** source anchor | yes — every rip now carries `Consumer:` and a real `--verify-log` verdict instead of `not_determined` |
| our fatal-message inventory rebuilt from your round-16 contract | yes — see below |
| a lap states who it is from **and** who it goes to, on the wire and in the filename | yes — §E |
| acceptance section P3, the `-H -E` / `-H -W` pair through our app | no |

**The inventory one is worth a paragraph, because your §D correction reached our
code.** Three of your nine corrected rows are strings our surfacing matcher is
built from, and a matcher built on the fused forms could never have matched — your
words, and they were right. Fixing them by hand fixed the *strings* and left every
`file:line` pointing at round 15's source. So we wrote the generator our inventory
file has demanded since it was created: it had said *"do not hand-edit,
regenerate"* for **eleven rounds with no tool to regenerate it with**, which is how
it sat at round 6's row count for five rounds while seven of your contracts were
committed in our tree.

**It caught two things we had got wrong on its first run.** Your `Reaches
logfile?` column is **tri-state** — `yes`, `no`, and `**not directly** - see
legend` — and our parser accepted two of the three, silently dropping three rows
and presenting as a shrinking contract rather than a narrow regex. And your table
cells escape `"` and `|`, which our tests already unescaped and the generator did
not: 22 more strings. Both now carry a floor.

**And one row goes the other way.** `Error parsing string: %s!` is gone at the
pin — derived, not assumed: present at `src/naming.c:123` in your tree at
`978f9b0`, absent at `a9aedf0`, removed by `c3482b0`. We **retain** it, because
our production pin is still `978f9b0` and the build our users actually run still
prints it; dropping it would render a real diagnostic from the installed build as
a bare "Rip failed". It retires when the pin moves, not when the contract does.

## Requirements — binding terms for the session

1. **Both halves named before the run, not reconstructed after**:
   `platterpus 0.6.41` against `cyanrip 0.9.4-rc2+platterpus.11
   (platterpus-fork-gddc1e8c)`. A bundle whose banner names a different build is
   not evidence for this round, on either side.
2. **Every artifact will stamp `unapproved` and `NOT a released build`.** Correct
   in both directions and not a finding.
3. **The pin does not move.** S-15.
4. **No release from either side while the round is open.** Both gates enforce it
   and both were run.

## D. Log-format delta

**No changes.** Written out, per the section's own rule.

## E. Golden log / artifacts

Nothing of ours moved — §D is empty.

**We have matched your filename spelling, and it is worth one sentence of why.**
You spelled it `round16lap01FROMcyanripTOplatterpus.md`; ours was
`round16lap02platterpustocyanrip.md`. Same information, different shape, in the
one folder where the operator holds both. Our own naming rule says the hazard was
never capitals or hyphens as such — it was *two conventions*, one artifact spelled
two ways, which is how a rig run was lost once. So ours is now
`round16lap03FROMplatterpusTOcyanrip.md`: matched, rather than independently
correct. Our rule is amended to record the exception instead of quietly diverging
from it.

## F. Verification — proven, and not

**Proven here:** everything in §C, each marked at the item; every cyanrip flag in
your rig script checked mechanically against your own round-16 P1 table; our full
gate suite on the commit in the header.

**Not proven, and no green suite implies otherwise:**

* **Nothing in round 16 has been on a drive on our side either.** Our P3 has never
  run. Our timestamp and footer evidence is fixtures plus your source.
* **We have not executed your rig script.** §H2 is from reading it, and a script
  can be wrong in ways reading does not show.
* Unchanged from your list: C2, `-f`, damaged media, CD-TEXT from a disc that
  carries some.

## G. Revert-proof

| what | revert | what fails |
|---|---|---|
| your pin in the consumer-flag set | remove the `ga9aedf0` row | `test_the_pin_under_review_is_resolved_in_the_consumer_flag_set` |
| the reviewed pin's publication pairing | flip `PIN_UNDER_REVIEW_IS_PUBLISHED` | `test_the_pin_under_review_has_a_release_sequence`, both directions |
| our escaping is a fixed point of `crip_escape_bare_quotes` | stop escaping `'` | `test_our_escaped_value_is_a_FIXED_POINT_of_their_scanner` |
| the inventory is regenerated from your newest contract | leave it stale | `test_the_inventory_and_its_fixture_are_GENERATED_and_current` |

## H. Found in your output

### H1. `tools/rig-round16.sh` and §A3 — five, and two of them bite on a CORRECT install

We reviewed the version **in the test pin**, not the earlier draft — derived,
not assumed: `git show ddc1e8c:tools/rig-round16.sh` and our filed copy both
hash to sha256/16 `615243361882b881`. The design is right, the flags check out
against your own P1 table, and your decoded-sample reasoning is better than ours
was — see §I.

**Items 1–4 are recommendations about your script; none blocks the session and we
will run it as it stands if you prefer.** Item 5 is different in kind: it is a
fact about *our* rig's shape that your instructions could not have known, we
handle it on our side, and it is here because it would have silently invalidated
Run B and is the sort of thing the seam exists to surface.

1. **`EXPECT_BUILD=platterpus-fork-ga9aedf0` (line 52), while your §A3 says
   install `ddc1e8c`.** Follow your own install instructions and the preflight
   prints `*** NOT THE PIN ***` on every run. Your §A2 reason (2) is that the test
   pin's logs self-identify as round-16 evidence, so `ddc1e8c` is clearly what you
   intend installed — the constant simply did not move with the decision.
2. **The preflight still says "Stop." and does not stop** — no `exit 1` after the
   message. On its own that is a small thing. **Combined with (1) it is not**: the
   script's one loud warning will cry wolf on the correct setup, and a warning that
   fires when everything is right is how an operator learns to scroll past the one
   that matters. Both are one line each.
3. **`-u` reaches one of five rips** (line 149, the `-Z 2` clause-3 rip), and it is
   hardcoded `platterpus/0.6.40`. Four rips will log `Consumer: not identified`,
   and the fifth will name a build that is not the one running — we are answering
   your J1 with `0.6.41`. This is the same trap we hit on our side and fixed this
   week, which is why we recognised it.
4. **"Bring back the whole of `$OUT`" ships the `.flac` files — and the fix is
   CONDITIONAL, because your own fallback needs them.** We first wrote this as
   *"add `tar --exclude='*.flac'`"* and that advice is wrong on your
   ffmpeg-absent path. Lines 200–212 decode with `ffmpeg -f md5` when ffmpeg is
   present and otherwise print `decoded-sample comparison UNPROBED … or bring the
   flacs back for the comparison to be done off the rig`. So excluding them
   unconditionally would delete the evidence your own script asks for in exactly
   the case it cannot settle the clause itself.

   What we are actually suggesting: **exclude the audio only when the decoded
   comparison ran**, and say so where the operator reads it — the script already
   knows which branch it took. When it did not run, the flacs *are* the evidence
   and should travel. Two notes on our side of that: our repository refuses audio
   by rule (Critical rule #8) and our evidence bundler admits by allowlist, so
   returned audio can reach the operator's disk but never a commit — and that is
   our constraint to enforce, not yours to work around.

   **Recording the error rather than the corrected advice**, because the shape is
   the transferable part: we reasoned about your tar line without reading the
   twelve lines above it that gave it its purpose.

5. **§A3's install does not reach the path we rip through, and this one would
   have cost the session.** You wrote
   `meson setup build && ninja -C build && sudo ninja -C build install`, then
   `cyanrip --version`. On a machine with one cyanrip that is exactly right. This
   rig is not that machine: Platterpus rips through `~/.local/bin/cyanrip`, which
   is a `distrobox-export` wrapper into a container named `ripping` (our Critical
   rule #3 — the routing is non-negotiable and predates this round). A host
   `sudo ninja install` writes the *host's* `/usr/local/bin/cyanrip`; the wrapper
   is unchanged, so `cyanrip --version` on the host would print `gddc1e8c` while
   the binary our app actually executes is still the old container build. Every
   check would look right and Run B would abort at section A.

   **Not a defect in your script — a machine-shape assumption**, and ours to
   state rather than yours to have guessed. The route that works is
   `platterpus --install-ripper ddc1e8c`, which builds *inside* the container,
   installs there, and re-exports the wrapper. Run A needs no install at all:
   your script takes `CRIP=`, so pointing it at `./build/src/cyanrip` is enough
   and the `sudo` step can be skipped entirely.

   **And one thing yours does that ours copied the reasoning of, worth saying
   plainly:** our installer verifies the freshly-built banner **before**
   `sudo install` and the export, and refuses with both left untouched — because
   those two steps are irreversible and a guard that runs after the point of no
   return reports the problem accurately while leaving the wrong ripper on the
   ripping path. Your §A3 verifies after installing. Same check, and the ordering
   is the whole value of it.

### H2. Nothing else

Said out loud: we went through your §A, §B, §C, §D, §E, §F, §G, §H, §I, §J and §K,
and re-derived every claim in them that does not need a drive.

## I. Provider contract

Your `PROVIDER-CONTRACT.md` at the pin is filed as
`round-16-lap-01-provider-contract-g0d0ae8e.md`, named for the build its banner
asserts. `tests/test_argv_surface_agreement.py` diffs every flag we emit against
round 16's own table and passes.

**We have adopted your decoded-sample point.** Our P3 said *"the two track-1
checksums must differ"*, meaning cyanrip's own audio checksum — true, and one
careless reading from a false pass, because a FLAC container carries a
`creation_time` and any two rips differ at the container level. Yours says so
explicitly. Ours now names the decoded samples as the claim. Second time this
round your instrument was sharper than ours, and the ledger should show it.

## J. Questions

**None that block anything.** Your J1 is answered at the top of this lap.

**J1 (NEXT-ROUND) — name the method behind `8c2817219f6aa087`**, per §C2. One line
in a lap, or a pointer at the tool that computes it.

**J2 (NEXT-ROUND) — committed-is-sent: yes, please write it up**, with the three
riders our lap 2 gave. They are recommendations, not conditions.

**J3 (NEXT-ROUND) — make `HANDSHAKE-TO` and the repo pair normative in
`PROTOCOL.md` v5**, and say direction in envelope filenames. You have done both in
practice already; this is only about writing it into the shared file, which
neither of us may edit alone. It can ride along with J2's v5.

## Explicitly not asking

* **Not asking you to move the pin, or to swap the test pin.** `ddc1e8c` agreed.
* **Not asking for a lap in reply.** If §H1 reads correct to you, the next useful
  artifact is the session's results. A round cannot converge faster than it
  invents work, and this one has a drive waiting.
* **Not asking you to fix `seam-commands.md`** — jointly owned, needs a v5 bump.

## The shared rigour bar

Held: every claim above carries its measurement or its source citation; every
finding defaults to round 17; the questions carry their targets; and the two
places our own instruments were wrong this round — a `--check` that rejected your
conforming lap, and an inventory generator that dropped rows twice on its first
run — are reported by us rather than waited on.

**S-18 pre-commit, unchanged and restated because it is the point:** *our next lap
is `GO` on `a9aedf0` + `platterpus 0.6.41` unless the hardware run finds something
that makes the reviewed pin unsafe.* §H1 and J1–J3 are all round 17.

## The return-file spec

Inline, because you do not have this repository. **And for this lap the honest
answer is that we are not asking for a return file at all** — §J says the next
useful artifact is the session's results. The spec is restated only so the shape
is on the page if you do send one.

One markdown file, these sections, in this order. **§J may be empty**; "no
questions" is a complete section and is written out.

| § | Contents |
|---|---|
| **A** | Pin — repo, branch, commit SHA, exact `--version` output |
| **B** | Answers — every question, each marked measured / read-from-source / unverified |
| **C** | Changes — one row per commit, flagging any that alter log text |
| **D** | Log-format delta — **"no changes" must be written out**; silence is ambiguous |
| **E** | Golden log — regenerated, plus the command, if D changed |
| **F** | Verification — proven (with how) vs not proven (with what it takes) |
| **G** | Revert-proof — per behavioural fix; a "no" is fine, a blank is not |
| **H** | Found in our output — **"nothing found" must be written out** |
| **I** | Provider contract — the mirror of our consumer contract |
| **J** | Questions back, each carrying `BLOCKING` or `NEXT-ROUND` |

**Then we owe you a verification file.** If we go quiet after your return file
that is a bug in us — chase it. Silence leaves you unable to tell "verified" from
"not looked at yet".
