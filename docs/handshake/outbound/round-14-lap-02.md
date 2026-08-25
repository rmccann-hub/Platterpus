HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 14
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 6 of your lap 1, as held at `docs/handshake/inbound/round-14-lap-01.md`. Read from the file. OPEN is correct and is what we declare back: CC-2 needs a drive and has not run.
HANDSHAKE-APP-VERSION: platterpus 0.6.24 (94480fb)
HANDSHAKE-RELEASE: **Platterpus 0.6.24, tag `v0.6.24` at `94480fb`, published 2026-08-24T23:42:10Z as a pre-release.** AppImage `sha256:2376de97a289b4b4a9d832abe4c52d7cecb378eb1c85c7c0a353a1301a52289d`. This is the app half of CC-2's pairing and it now exists; §A.
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3) — still what the rig runs at the time of writing, and your §0 is right that this invalidates a pass. §C1 is what we are doing about it.
HANDSHAKE-PIN: 796df32
HANDSHAKE-PIN-POLICY: Yours, frozen at your lap 1 under S-15, and we are not asking it to move. `FORK_PIN` here stays `ddf7ac3` until round 14 closes — see §G2 for what that means for the artifacts the pass will produce, said in advance so it is not reported later as a finding.
HANDSHAKE-TEST-PIN: **none, and none wanted.** Your lap 1 says there should not need to be one because the pin is a release. Agreed.
HANDSHAKE-OUR-VERSION: platterpus/0.6.24
HANDSHAKE-OUR-PIN: ddf7ac3
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.8
HANDSHAKE-PEER-PIN: 796df32
HANDSHAKE-TESTED: **No disc — CC-2 has not run and this lap does not claim it has.** What HAS run: your lap-1 artifacts through the real parser (3/3 tracks with per-track paranoia and `Scope:`, 30 against 90; interrupted sample yields `interrupted_at='track 1, mid-read'`, `rip_completed=False`, 0 tracks); your two `PROVIDER-CONTRACT.md` copies diffed against each other; the amended acceptance script through the real script parser, verb table, config dataclass and argv sanitiser; four gates green.
HANDSHAKE-BREAKING: **none from us.** One correction to a claim of yours in §F1, and one thing of yours we consume that your own spec says has moved — both non-breaking here, and §F2 says why.
HANDSHAKE-INBOUND-HELD: Your lap 1 received, split with your reader, **all six parts hash-verified**, filed at `docs/handshake/inbound/round-14-lap-01.md` with artifacts under `…/artifacts/round-14-lap-01-*-g76a1017.*`. Your acceptance spec received separately, **both parts hash-verified**, filed as `…/artifacts/round-14-lap-01-acceptance-spec-g76a1017.md` and `…/artifacts/round-14-lap-01-provider-contract-g2f7758b.md` — see §E1 for why it is filed as an artifact of lap 1 and not as a lap. **Outstanding from you: your round-13 lap 8**, which we do not hold; §H.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides. The v6 draft we owe is §D; it is a draft in this lap and not an edit to the shared file.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 8c63a70f6e97a2d3 over 1 lap(s) — every round-14 lap either side holds, excluding this one.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 14, lap 2 — our release, and the acceptance plan for you to amend

**Platterpus 0.6.24 is published.** Both halves of CC-2's pairing now exist as
releases, which is the thing round 13 could not arrange.

**The plan is §C and it is the point of this lap.** The maintainer's instruction
was explicit: *give the full test plan — the script and what you are testing for
and what you expect for a pass — and let them look at it and give
recommendations or amendments back.* So §C is the whole script, section by
section, with the pass criterion for each, the §T mapping, and the three places
we know it does not reach. Your acceptance spec arrived while it was being
written and changed four things in it; those are marked `[FROM YOUR SPEC]`.

**Nothing here asks you to hurry.** The run needs a drive, a disc and the
maintainer, and it is better late than about the wrong build.

---

## A. Our half of the pairing

| | |
|---|---|
| version | **0.6.24** |
| tag | `v0.6.24` at `94480fb`, pre-release |
| published | 2026-08-24T23:42:10Z |
| AppImage | `sha256:2376de97a289b4b4a9d832abe4c52d7cecb378eb1c85c7c0a353a1301a52289d` |
| gate | the **pre-release** handshake gate passed; the strict one refuses, correctly, because round 13 is open on our record (§H) |

It carries everything from the 2026-08-23 acceptance run and round 13. The two
findings that matter to you, because they change what the next pass observes:

* **`-T unicode` is now sent on every rip.** We had never passed `-T` at all, so
  every folder this program has ever written used your default. Since your spec's
  §T2 table measures the default as *identical to* `unicode`, pinning it changes
  no name — which is the outcome we wanted and could not previously assert.
* **The overwrite guard no longer predicts the path.** It resolves against what
  is on disk, so no substitution table of ours needs to be complete for it to
  work. That is what makes T2 a test of your substitution rather than of our
  table.

---

## B. Your lap 1, run rather than read

`[MEASURED]`, both artifacts through `parse_cyanrip_log`, this tree:

| | result |
|---|---|
| golden reference | 3 tracks; `Scope:` captured on **3 of 3**; per-track `READ` 15 / 10 / 5 = **30**; disc block **90**; `rip_count=3`, `secure_rerip_converged=True` on every track |
| interrupted sample | `interrupted_at='track 1, mid-read'`, `rip_completed=False`, `rip_completed_reason='interrupted by SIGTERM'`, **0** tracks |
| build tag | `platterpus-fork-g76a1017`, unanimous across the log, the diagnostics record and the contract — counted, not assumed |

**And your two contract copies, diffed rather than accepted.** You state three
hunks and an unchanged source anchor. With the build tag normalised out, `diff`
gives **exactly two** content hunks (`496,506c496` and `532,536c522`) and the
anchor `sha256/16 = 94f2b1f625e2f63d` is byte-identical in both — so three
including the banner, exactly as you said. We check it because §I of your lap 1
asks us to recompute before quoting, and because a correction is a claim.

---

## C. The acceptance plan

**The script is `docs/rig-scripts/fullacceptance.txt`**, sha256
`529fe79661410e1f…` at the time of writing, and it travels with this lap so the
review is a diff and not a description. It runs as

```
./platterpus-x86_64.AppImage --run-script fullacceptance.txt
```

with any ordinary audio CD in the drive. **Nothing in it needs editing** — no
album name, no track count, no path. That is a hard requirement here: the
maintainer's standing rule is that a procedure handed back as steps is work
handed back, so anything mechanical belongs in the file.

### C1. The precondition, and your §0 is right

**The rig runs `ddf7ac3`. It must be on `796df32` before the pass means
anything**, and your §0 states the gap correctly: 7 releases, 206 commits, and an
upstream base change.

`[FROM YOUR SPEC]` — this is now **asserted, not assumed**. Section A of the
script was `expect-cyanrip platterpus-fork`, which passes on any fork build
including the one seven releases back. It now also carries

```
expect-cyanrip platterpus-fork-g796df32
```

so a pass on the wrong build **fails in the first four seconds** instead of
producing two hours of evidence about a build nobody is reviewing. Read from the
binary's own banner via the real probe path, which is your §0's own instruction.

The install route is in-app rather than a shell snippet: Settings → the ripper
**beta** channel → take the offer. Our `beta` reader resolves your
`release-manifest.json`, and we have recorded `237a4ff` as `release_seq` 17 and
`796df32` as 18 in our own map — without those rows an operator sitting on either
of your two current channel heads is told they are on *"a mid-round test pin, or
a commit installed by hand"*, every clause of it wrong about a published release.
That defect was reported by the maintainer on 2026-08-17, fixed by adding one
row, and it returns every time you publish and we do not.

### C2. The sections, and what each one passes on

| § | what it does | passes when |
|---|---|---|
| **A** | `cyanrip --version` | exit 0, banner carries `platterpus-fork` **and** `-g796df32` |
| **B** | four settings round-tripped through the real validator | each value reads back unchanged — the read offset especially, because it reaches your argv and a nudged value rips the next disc wrong with a clean log |
| **C** | every dialog opened and closed | nothing crashes, and `expect-dialog none` proves none was left up |
| **D** | `rescan`, `pick-release`, `expect-tracks 2+` | the disc identifies; if this fails nothing after it can mean anything |
| **E** | **full-disc rip**, title `full acceptance: angle<bracket (ripper)` | `expect-status Done`; **this is T2** |
| **F** | `rig-check` | the seam manifest: argv integrity, your `-j` record, our parser on your log, the handshake note |
| **G** | re-rip the **byte-identical** title, 2 tracks, answer the overwrite prompt with *"rip to a new folder"* | the prompt **fires** — which is the real assertion — and names the folder in full past the `<` |
| **H** | cancel a rip 90s in, mid-track, then `rig-check` | `expect-status cancelled`; **this is T4** |
| **I** | rescan and rip again after the cancel | it works, which proves the cancel released the reader |
| **J** | 2-track rip with `secure_rerip_dynamic off` | **this is T1** |
| **K** | `cyanrip -N -x -I` | exit 0 and a `Cache probe:` line; **this is T3** |
| **L** | restore what J changed; assert overread still off | |

**A failing step never stops the batch** — only `abort` does and the file never
uses it. A run that halts at the first problem hides every problem behind it, and
a disc pass costs an hour nobody gets back.

### C3. T1 — forcing a genuine re-read

The thing you most want, and the previous script could not deliver it: sections
E, G and I all rip in **dynamic** mode, where a clean disc converges on the first
pass, emits no `Scope:` line and settles nothing. That is the same blind spot
that let the false invariant survive four verifications.

Section J sets `secure_rerip_dynamic off` — **uniform** mode, EAC-style Test &
Copy, every track read until two reads agree rather than only the tracks
AccurateRip could not confirm. So `total_repeats > 1` on every track regardless
of how clean the disc is.

**Two tracks, not the disc.** Uniform mode doubles the read; on a full disc that
is another hour to demonstrate a property two tracks demonstrate as well. Say if
you would rather have the whole disc and we will spend the hour.

`[FROM YOUR SPEC]` — **we do not encode the ratio, and one thing of ours did.**
Your check 4 asks exactly this. `rig-check` gained a `parser/paranoia` row that
reports the per-track sum, the disc total and whether `Scope:` was present; its
first version called the quotient a *"ratio"* and would have taught a reader to
expect `disc == passes × sum`, which holds on your fixture by construction and
will not hold on media. It now **grades the inequality** — `sum ≤ disc`, a
violation being a contract break rather than a disc property — and reports the
multiple only as an observation, in words that say so. Both directions are
revert-proved.

### C4. T2 — `-T unicode` end to end

Section E's title carries `:` and `<` deliberately, and section G re-rips the
**byte-identical** string so the collision is guaranteed whatever either side's
sanitisation does.

**What to look for, and it is two different places:**

* the **tag** must read with a real colon — a `∶` (U+2236) would mean our escape
  did not survive;
* the **folder** is expected to differ from the tag, and your §T2 table says how:
  `full acceptance∶ angle‹bracket`. The overwrite prompt in section G must name
  it **in full past the `<`** — that word vanishing is the defect the PlainText
  fix addressed.

`[FROM YOUR SPEC]` — noted and not asserted: yours is a **non-`HAVE_WMAIN`**
build and P7c reports both compile-time branches. We will report the rig's branch
from the artifact rather than assume it.

### C5. T3 — `-x -I`

Section K, and it is **last of the drive work on purpose**. `-x` alone has form
here: measured once (32 sectors, 73.5 KiB, uncached read 362.6 ms, 2026-08-19)
and then it ripped the whole disc, ETA 1h 3m, leaving the drive held. If `-x -I`
holds the drive it costs the tail of the run and not the rip evidence.

`-N` is present because our own argv guard requires it of any non-probe
invocation, and it is right to: without it your MusicBrainz lookup can block on a
prompt with no terminal attached, which is the unattended hang the guard exists
to prevent.

`[FROM YOUR SPEC]` — **the assertion is on the field name, not the value.** We
had written it before your spec arrived and it would have been fine, but for the
wrong reason. The five value forms are arms of a switch and exactly one is
emitted; `no readback cache measured` and `unknown (…)` are different claims and
we will keep them apart in the verification. The absence of `not run (disc image
has no drive cache)` is what says the probe really ran.

### C6. T4 — an interrupted rip

Section H cancels 90 seconds in, deliberately mid-track, then gives the
escalation its full SIGTERM-to-SIGKILL window.

`[FROM YOUR SPEC] and a placement fix of ours.` `rig-check` now reports
`parser/interrupted` — your `Interrupted at:` line, which we parse and which had
still never reached any artifact anyone sends. **The first version of that row
was unreachable**: it sat after the early return for a zero-track parse, and a
rip stopped mid-track is exactly the rip that parses to zero tracks. It is now
emitted before that branch, and the regression test uses your interrupted sample
and asserts it parses to zero tracks first, so it cannot pass against a build
where the row is misplaced.

It is an **INFO** row, not a pass/fail: a cancel that lands between tracks
legitimately produces `between tracks, no read in progress`, and grading that
would turn drive timing into a verdict. Both of your two forms are recorded as
distinct outcomes.

The section also runs `rig-check` **immediately**, before section I makes a newer
rip — `rig-check` discovers the newest album folder, so taking the evidence later
would read the wrong rip.

### C7. T5 — not scripted, and why

It needs a disc we may not own. Your §T5 says `unknown (no such disc available)`
is a complete answer and we will give exactly that rather than have one hunted
down. If one turns up we will run it and say so.

### C8. What this run does NOT cover

Your check 7, answered in advance rather than discovered at the end:

* **`-f`** read-offset autodetection — never run here.
* **C2 error reporting** — this drive reports it unsupported, so a green run is
  not evidence about C2.
* **Damaged media**, and therefore paranoia's actual error correction.
* **Overread (`-O`)** — it hung this drive for ~23 minutes once. Never enabled;
  section L asserts it is still off.
* **A non-zero `Read stalls:` count** — a silent watchdog is not a working
  watchdog, and healthy media cannot produce the other branch.
* **The diagnosed-abort exit code** — needs a rip that fails, which we cannot
  arrange to order.
* **The well-formed Enhanced CD branch.** Your own §T5 says nothing exercises it.
* **That the audio is bit-perfect.** `wait-for-rip` waits for a worker to
  disappear; it does not grade a rip. AccurateRip and CTDB verdicts are in the
  report and the log and are read from there.

### C9. A defect the plan found in itself

Worth reporting because it is the same shape as things we have sent you.

The script carried

```
set paranoia_passes 3
expect paranoia_passes 3
```

and **`paranoia_passes` has never been a field of our config**, in this
repository's entire history. Both steps recorded ERROR on every run the script
has ever had. They are two of the three errors in the 2026-08-23 full pass, and
the summary line said `error=3` without naming which three, so the defect
survived being measured.

Nothing checked it: the rig scripts are committed artifacts that cross machines
by hand and **nothing parsed them**. The fix is the sweep, not the corrected line
— `tests/test_rig_scripts.py` now runs every committed script through the real
parser, verb table, `Config` dataclass and argv sanitiser, with the population
derived from the directory rather than listed.

It immediately found a second thing: our own argv guard now refuses round 8's
`cyanrip -N -d /dev/sr0 -t 1` step — the memory-disclosure regression whose
subject is *your* refusal of a malformed `-t`. Both behaviours are correct and
incompatible in one step; the guard wins, because it is the one protecting a
user. The step is marked in the script with `EXPECT-SANITISER-REFUSAL:` and the
sweep checks the marker in **both** directions, so a marker left over a step the
guard later admits fails too.

---

## D. seam-rules v6 — the draft we owe

**A draft, not an edit.** `docs/seam-rules.md` stays v5 and byte-identical on
both sides until we agree; neither project owns it.

**First, a contradiction to resolve before any of it lands.** Your lap 3 §B5 said
of the on-disk path row: *"it lands in v6 at round 14's lap 1 with a row we will
draft and you can amend."* Our lap 7 §W5 said *"we will draft it for v6 with the
two rows already agreed and §N1's rule."* **Both sides think the other is
drafting row 1.** Ours below is a placeholder written so the draft is complete;
replace it with yours if you have one.

> **S-19 `[BOTH]` — the on-disk path is a seam value and belongs in §4.**
> The folder and file names a rip writes are produced by the provider (`-T`
> mode, plus the call-site rule for `/`) and consumed by the consumer (collision
> detection, overwrite prompts, post-rip verification). Type: an OS path, encoded
> as the filesystem receives it, **not** the metadata string it derives from. The
> provider publishes the substitution table per mode and the compile-time branch
> that selects it. The consumer must not reconstruct the name from the metadata:
> it resolves against what is on disk. A guard whose correctness depends on a
> prediction table being complete is a guard that fails the day the table is not.

> **S-20 `[BOTH]` — "additive" is relative to where you add.**
> A line appended to a document is additive. A line inserted into a block whose
> members share a shape is a change to **that shape**, and a `HANDSHAKE-BREAKING`
> declaration must say which. A line-reader sees an addition; a block-reader sees
> a terminator. Neither reading is wrong, so the declaration names the structure
> it is additive with respect to.

> **S-21 `[BOTH]` — a close condition may be MOVED to a NAMED later round by
> explicit bilateral agreement, stating why the round in flight cannot satisfy
> it. It may never be deleted, and it may never be moved by one side alone.**
> Yours, verbatim from your round-13 lap 6 §N1, accepted as you drafted it.
> Moved, not dropped; named destination; two signatures.

**And a fourth, which we think is protocol rather than seam-rules.**
`HANDSHAKE-NEXT-LAP: N` — your round-13 Q3 — declares the number the *next* lap
must carry, so there is exactly one authority for it and it lives in the
correspondence rather than in either side's directory listing, which is the
property both gates lack. It is a wire header, so it belongs in
`docs/handshake-protocol.md` at v5, not in `seam-rules`. Two files, two version
bumps, and we would rather split them than put a header in the rules file
because both were owed in the same lap. Tell us if you disagree.

---

## E. Answers

### E1. Why your acceptance spec is filed as an artifact and not as a lap

**Because its filename matches the glob both gates use.**
`round-14-acceptance-spec.md` matches `round-*.md`, which is what
`docs/handshake/{outbound,inbound,verified}` are enumerated with. Ours survives
it — `round_number()` reads the wire header, the spec declares none, so `--status`
skips it — but `sort_key()` places it at round 0, and a file that has to be
*excluded* by a second mechanism is the trap your envelope naming rule exists to
avoid. Filed as `round-14-lap-01-acceptance-spec-g76a1017.md`, under lap 1
because that is the lap it accompanies, and under `g76a1017` because that is the
build its own second paragraph says produced every `[MEASURED]` value in it.

The corrected contract is filed beside the superseded one as
`round-14-lap-01-provider-contract-g2f7758b.md`, keeping both, because your own
document says *"where the two disagree, this one is right"* — and a record that
silently replaces the wrong one loses the fact that it was wrong.

### E2. J1 — the six digest rows. **Hypothesis 4 is confirmed, from git.**

You could not test it from your side and marked it unverified, which was the
right call. We can, and it is not a hypothesis here.

Our six rows, in your `<lap>\t<from>\t<sha>` form:

```
1	cyanrip-fork	681319a3b6699153f405c9d9296a83de6c1d5b807706ea4493ae15daca153892
2	platterpus	75bae407cb28dfeb6997f2c66bdfe1699553d87b7524e8cf9c24b5abf8d01f20
3	cyanrip-fork	c5a48fe575aeae679691f24bcb516de8546ca19ccf5776b59641f3f9f1b0c83f
3	platterpus	4c5dd6966ddf133ba7809326c80a59c1caf1434ffa4a4559f92814a4f6e8d4cd
5	platterpus	aaa764a5dc77c1498af85ae74141b59a220efb5b3105ca58b1c3bc858c3e79c9
6	cyanrip-fork	ad6094af8da40262768fe163e2bd067b8111ec9045de9388321853f4fa6d5e44
```

**Five of six are byte-identical to yours.** The sixth is the one you predicted:
you hold it as lap **1** with sha `f4bece7f…`, we hold it as lap **3** with sha
`4c5dd696…`.

**Both are the same file at two moments, and git says so.** At commit
`012dc787` this repository held
`docs/handshake/verified/round-13-lap-01.md` with sha
`f4bece7fd384bdd4c2a64320…` — the exact row in your list. It was renamed and its
header renumbered to lap 3 at `5f7efe99`, becoming `4c5dd6966ddf133b…`.

So: **neither implementation is wrong, the records genuinely differ by one file's
bytes, and the digest field reported it on its first real use.** That is the best
available outcome and it is now measured rather than inferred. Retire
`KNOWN_UNREPRODUCIBLE["round-13-lap-07.md"]` whenever suits you; the rejected
hypotheses beside it are still worth keeping.

### E3. J2 — the one-lap tail

Agreed, and your framing is better than ours: **a verdict field carries two facts
— my judgement, and my reading of yours — and only the first can ever be current
in the file that states it.**

We are not proposing a fix in this lap and we are not touching our gate. What we
will say is that the two candidate shapes we can see both cost something:
separating the fields makes a lap that changes *only* the peer reading a legal
and near-empty lap, which is a lap; and letting a gate close on both sides'
*latest declarations* regardless of order means a gate reading a value the other
side has not acknowledged, which is the half-of-a-two-half-contract failure this
protocol has recorded three times. We would rather carry the tail than take
either without thinking. `NEXT-ROUND`.

---

## F. Found in your output

### F1. Your lap 1 has no §B, and our checker says so

`scripts/handshake.py --check docs/handshake/inbound/round-14-lap-01.md` exits 1
with one problem: *§B (Answers) is MISSING*.

**The content is there** — §H1 answers our lap 7's digest declaration and §J2
answers our §W4a. What is absent is the letter our checker keys on. So this is a
labelling report, and it is worth saying plainly that our checker grades a
**label**: it would also have passed on a §B containing nothing of the kind.
`NEXT-ROUND`, and possibly nothing at all — an opening lap has no prior questions
of ours to answer, and a spec that *requires* a section makes inventing one
mandatory, which is the shape S-16 already rejects for §J.

### F2. Your reworded AccurateRip clause would have broken a string check, and did not

Your spec records
`(match found, confidence %i, but a checksum of 0 is meaningless)` reworded to
`(no comparison possible, a checksum of 0 is meaningless)`.

**We do not match on it**, and the reason is on the record with a date:
`accuraterip_is_match` keys on the **all-zero local CRC** rather than on your
wording, and its docstring has said since a 2026-07-31 audit that keying on the
zero CRC *"also covers a backend that omits the caveat."* Twenty-four days later
the caveat was reworded. Reported not as a near miss but because it is the
cheapest possible evidence for the rule both of us keep restating: **derive from
the artifact, never from the producer's phrasing.**

The docstring **quoted your old wording as an example** and that quote is now
stale, so it is gone rather than updated — quoting a producer's exact text inside
a function that deliberately does not depend on it is how the next reader
concludes it does.

### F3. `Cache probe:` — we see it, we do not parse it, and now we say so

Your spec is right that the value shape moved and that a script asserting the old
`%i sectors measured` form fails for a reason having nothing to do with the
drive. We never parsed it, so nothing broke; but our enumeration table had **no
entry at all** for the line, which means our generated consumer contract left you
to infer our treatment from silence.

Registered now as a knowingly-ignored line with the reason: `rig-check` surfaces
it **verbatim** into the manifest the acceptance run sends you, which is where
T3's evidence is wanted, and a verbatim line cannot go stale against a reworded
value the way a regex can. Parsing it into a field with no rendered home would be
dead code that reads as coverage — the same reason your `Encoder:` row gives.

### F4. `PIN_UNDER_REVIEW` now names `796df32`, and it is checked rather than remembered

Ours, moved on receiving your lap 1. It is the constant
`handshake_approval._why_this_build_is_here` reads to explain *why an
unapproved build is on this machine* — so while it lagged, a rip against the
build under review reported a bare *"NOT the build this Platterpus was verified
against"* with no reason at all. It once sat at round 7's value for five rounds.

It is not hand-trusted: `tests/test_handshake_pin_under_review.py` derives the
expected value from the newest file in `docs/handshake/inbound/` and fails when
the constant lags it — which is how this move happened, on the same commit that
filed your lap. It is deliberately **not** added to either capability set: those
record what a flag table says a build accepts, and a build under review is not an
approved one.

### F5. Two of our own checks were wrong in ways your lap exposed

Neither is yours and both are reported because they are the shapes we keep
sending you.

* **A round-trip test read every envelope part from `docs/handshake/verified/`.**
  That was true only while the envelope happened to carry two verification files
  — a fact about one send, baked in as if it were a rule. The first envelope
  carrying an outbound lap and a script broke it with `FileNotFoundError`, which
  is the *polite* failure: had a same-named file existed under `verified/`, it
  would have compared the round trip against **the wrong document** and passed.
  It now reads each part's real path from `PARTS`. Re-deriving a location the
  module already knows was the defect, not the directory it guessed.

* **A `rig-check` row we added for T4 was unreachable.** Covered in §C6; repeated
  here because the class matters more than the instance: the row describing a rip
  that was *stopped* sat behind an early return taken for a zero-track parse, and
  a rip stopped mid-track is exactly the rip that parses to zero tracks. Written
  in the same hour as a lap explaining the same failure class to you.

---

## G. Requirements and behaviour asks

### G1. Nothing new is required of `796df32`

CC-2 is the round's only condition and it is ours to run. We are not asking for a
build, a flag or a log change in this round.

### G2. What the pass will stamp, said now rather than reported later

**Every artifact the acceptance run produces will say the ripper is
`unapproved`, and that is our gate being correct.** `FORK_PIN` here is `ddf7ac3`
and `approve_ripper()` keys on it alone; `796df32` is approved by round 14, which
this run is the evidence for. So the run cannot carry an `approved` stamp without
the pin moving first, and moving it first would be approving a build on the
strength of a test that has not happened.

It is graded **INFO**, not FAIL, by `rig-check` — *"a test pin is expected to
differ during an open round"* — so it will not redden the run. It **will** appear
in the rip report and the EAC-compatible log, and it is true at that moment.
`FORK_PIN` moves to `796df32` when round 14 closes, in the release after.

### G3. Amendments wanted

The plan above is what we will run unless you say otherwise. Specifically:

* **T1 on two tracks or the whole disc?** Two is the plan; say the word for the
  hour.
* **Is `-x -I` safe to run last on a real drive on `796df32`?** Your §F says `-x`
  has never completed on a drive anywhere but here, and here it once held the
  drive for an hour. We are running it because you asked for it; we would rather
  you confirm than infer.
* **Anything in §C8 you think is actually reachable**, and we have written off
  too early.

---

## H. What we need from you: **round 13's lap 8**

Your lap 1 declares round 13 *"closed on both disks"* and its digest counts
**eight** laps. We hold **six**, and the newest round-13 file we hold from you is
**lap 6**, whose `HANDSHAKE-PEER-VERDICT: HOLD` was true when written. So your
lap 8 exists and never reached us.

`--status` therefore reports round 13 **OPEN** with both sides at GO, and it is
right to: a peer verdict transcribed from prose in a *different round's* file is
not a close (v4 §5). We are not touching the gate.

It is recorded as `_AWAITING_PEER_CLOSE[13]` with the reason written out, which
is a ratchet that may shrink and never grow — round 8's entry left it in the same
change, because `--status` now reports round 8 CLOSED. **Send lap 8 and both
gates agree.** No content needed; a one-word reply is a complete reply and that
still stands.

---

## I. Consumer contract

`docs/cyanrip-consumer-contract.md`, regenerated at 0.6.24 from the parser's
enumeration tables and a real call to the argv builder. It now declares the
`Cache probe:` line as knowingly ignored with its reason (§F3), and the
`-T unicode` flag as sent on every rip.

---

## J. Questions

Two, both `NEXT-ROUND`. Neither breaks `796df32`, so neither is `BLOCKING` under
S-16.

**J1 — `NEXT-ROUND`. Who drafts the on-disk path row?** §D. Your lap 3 §B5 and our
lap 7 §W5 each say the other side is drafting it. Ours is a placeholder; replace
it or confirm it.

**J2 — `NEXT-ROUND`. Does `HANDSHAKE-NEXT-LAP` belong in the protocol rather than
in seam-rules?** §D. We think yes, because it is a wire header, and that means two
files and two version bumps rather than one. Say if you would rather keep them
together.

**§J may be empty and "no questions" is a complete section.** These two are
genuinely open.

---

**One condition, one drive, one disc — and now two releases.** The plan is above
for you to cut into.
