# TASKS.md — Platterpus Active Task Checklist

Single source of truth for what's being worked on next. Update status as work progresses:

- `[ ]` / ⬜ not started
- `[~]` / 🟡 in progress
- `[x]` / ✅ complete
- `[?]` / ⛔ blocked (add a one-line note about what's blocking)

The **bullet** task lists below use `[ ]`/`[x]` (GitHub renders these as real
checkboxes). The **numbered** sections ("Current plan & priorities", "Ranked
execution order") use the emoji equivalents instead — GitHub only renders
checkboxes in bullet lists, so a numbered `1. [x]` would show as literal text;
the emoji means the same status and keeps the rank numbers (referenced elsewhere
as "item N" / "TASKS #N") intact.

Execute tasks in priority order. P0 shipped 2026-06-01 as v0.1.0; the P1 backlog has been the active queue since.

When a task changes status, update it here in the same commit as the code change. When a task uncovers a new sub-task, add it to this file; don't let it live only in chat.

---

## Found on the rig, 2026-08-12 — the round-8 script run that never reached the rip

Three defects, all ours, all found by a real hardware run of
`docs/rig-scripts/round08joint.txt` on the Bazzite + BDR-209D rig. The run
scored 62 pass / 10 fail and **the rip never started**, so it produced no round-8
evidence — but it produced these.

**All three are fixed and shipped in v0.6.12b2** (2026-08-13), together with a
fourth the fork reported separately (`expect-cyanrip` could not express a string
containing a double quote). Boxes ticked below with what each turned out to be —
kept rather than deleted, because the *diagnosis* of the first one is the part
worth re-reading and it is not what the symptom said.

- [x] **BLOCKER — the disc scan is killed by a 0 ms grace, so no disc identifies
  and no rip can start.** *Fixed in 0.6.12b2 — and the 0 ms was innocent.*
  `DrivePicker.set_drives` re-emitted `drive_changed` when a repopulate restored
  the **same** device, which is a no-op by definition; the second emission four
  seconds into launch superseded a healthy scan for no reason. Superseding really
  does need to be immediate (a probe blocked in `subprocess.communicate()` cannot
  be asked politely to stop), so the wait is unchanged. **When a mechanism is
  correctly violent, audit its trigger, not its force** — the second of the two
  questions below was the wrong one to fix, and fixing it would have left the
  scan still cancelled and restarted, just more slowly. Original notes: `drive changed: /dev/sr0` fires **twice** during
  startup (02.978 and 06.823 in the rig log); the second cancels the in-flight
  `DiscInfoWorker`, which is then abandoned with *"did not stop within 0ms"* and
  its cyanrip child is SIGKILLed mid-TOC-read — surfacing as
  `cyanrip failed (exit -9) with no output`. Start rip stays disabled, so
  `rip` fails with *"the Start button is not enabled"* and the whole unattended
  run is lost. A **zero**-length wait is the same family as `CLAUDE.md` rule #9's
  *never hand `QThread.wait()` a negative number*: no grace at all is not a
  bounded wait, it is a kill. Two questions to answer together — *why does the
  drive-changed signal fire twice from one startup*, and *why is the cancel
  budget 0 ms*. Fixing only the second leaves a scan that is still cancelled and
  restarted for no reason. Present in 0.6.11 and 0.6.12b1 alike.

- [x] **A refused `cyanrip` step leaves the PREVIOUS invocation as the comparison
  subject.** *Fixed in 0.6.12b2: a refusal now clears `_last_cyanrip_*`, so the
  following assertion reports "no cyanrip command has run yet".* On the rig, `L260` was refused (the `-t 1` guard) and `L261`'s
  `expect-cyanrip` then compared against the output of `-p ==`, two commands
  earlier; same at L283/L284 and L315/L316. It failed loudly this time, which is
  luck — the stale command could just as easily have contained the expected
  string and reported a **pass for a step that never ran**. That is the
  *satisfied by the wrong thing* shape, inside the surface this project's tests
  are written in. A refusal must invalidate `_last_cyanrip_*` so the following
  assertion fails as *"no cyanrip ran"*.

- [x] **`expect secure_rerip_dynamic True` measures the operator's config, not
  the behaviour.** *Fixed in the script, not the code: B2 now `set`s both fields
  before asserting them. Still to correct to the fork in lap 10.* Failed on the rig (`got False`) because that install has it
  off. Round 8 lap 8 §J9 told the fork "both defaults are what B2 asserts, so B2
  passes on a default install" — accurate about a *default* install and useless
  about this one. A test that asserts a setting it did not set is testing the
  machine. Either `set` it first, or asserting it is the point and the script
  should say which. Correct this to the fork in lap 10.

- [ ] **The setup wizard silently rebuilds the production pin over a test pin.**
  Found while answering the fork's J10 (*"what reverts our binary?"*) from source
  rather than from memory: nothing reverts it at launch, and the only code running
  `git checkout --force --detach <pin>` is the setup wizard and `--install-ripper`,
  both explicit. But the wizard builds `WIZARD_TARGET` (= `PRODUCTION_TARGET`), so
  an operator running a test pin who opens the wizard for any other reason —
  a missing encoder, a drive question — gets it **downgraded with no warning**,
  which is exactly the shape of every revert in their reflog landing on `ddf7ac3`.
  The wizard should say *"this will replace cyanrip <test pin> with <production
  pin>"* and let the operator decline. Deliberately **not** fixed mid-round
  (S-14: a real defect that does not break the artifact under review).

## Ripper install: find the newest build automatically, and let the user pick its channel (2026-08-07)

**The maintainer's ask, verbatim:** *"in the future it should be automatic that it
looks for the most recent version, and give an option between a full release and a
beta/alpha."*

Prompted by having to hand-correct the pin twice in one day — `9048082` → `422d12a`
→ `ddf7ac3` — each time by editing a constant and cutting a release. The pattern is
real and the ask is right.

**The constraint that shapes the design, stated first because it is the whole
difficulty:** the pin is not a convenience, it is the handshake's subject. A round
approves a *named commit* for a *named app version*, `handshake_approval.py`
verifies every rip against it, and the deviation policy forbids moving it while a
round is open. **An installer that silently fetched "the newest" would defeat the
protocol both projects spent 41 laps building.** So the automation cannot be "keep
up to date"; it has to be "notice, and offer."

- [ ] **Detect that a newer fork build exists, and say so.** Not install it. The
  dependency screen and the wizard already name the installed build tag; they
  should also be able to say *"the fork's `platterpus-fork` branch is now at
  `<sha>` (`<version>`), which no round has approved."* Read the branch head via
  the GitHub API and the version out of `meson.build` at that commit — **there are
  no tags to read**: the fork's git proxy refuses tag pushes, which is why the
  commit sha is the only resolvable release identifier (see `fork_source.FORK_PIN`).
- [ ] **`--install-ripper latest` / `latest-beta`**, resolving the newest commit on
  the branch instead of requiring a sha typed by hand. The flag already takes an
  arbitrary commit (`target_for_commit`), so this is a resolver in front of an
  existing seam, not a new install path.
- [ ] **A channel choice that mirrors the app's own.** Platterpus already has
  `update_channel` = `stable`|`beta` with an explicit warning before a pre-release.
  The ripper should read the same way, and for the same reason: *being handed a
  tester build is a different thing from being handed an update.* Reuse the
  vocabulary rather than inventing a second one.
- [ ] **Every non-approved install must be visible in the artifact, not just at
  install time.** This half already works — a rip on an unapproved build reports
  `ripper_handshake_approval: unapproved`, and `not_determined` for an unrecognised
  tag — and it is what makes the rest safe to offer. Confirm it still holds for a
  build resolved automatically, since that is a path it has never taken.

**Do not** make any of this the default. The default stays: install what a closed
round approved. The automation's job is to stop the *maintainer* hand-editing a
constant, not to move users onto unverified builds.

## What v1.0.0 needs, named before anyone is tempted to declare it (2026-08-07)

**S-17 applied to our own versioning.** Round 7 took 38 laps because its evidence
was *"a rip"* — not a thing anyone can be finished with. The maintainer declined
1.0 for a precise reason and it should not be left in a chat log:

> *"we've only had my hardware and a small amount of albums yet."*

`v0.6.4` is honest about what it is. `v1.0.0` is a claim of stability, and the
evidence for it does not exist yet. Naming it now means nobody has to argue about
the finish line later — and if any row turns out to be the wrong bar, that is a
decision to take deliberately rather than by drift.

- [ ] **More than one drive.** Every hardware result this project has is from one
  Pioneer BDR-209D 1.51 at offset +667. A read-offset bug, a speed-lock quirk or
  a cache behaviour that is drive-specific is invisible in a sample of one, and
  the offset path is the single most correctness-critical thing we do.
- [ ] **More than one machine.** Bazzite + KDE Plasma 6 is the primary target and
  the only one anyone has run. Fedora/Arch/Ubuntu are claimed in the README and
  unverified by a person.
- [ ] **A disc sample with the awkward cases in it, not just more of the same.**
  Currently: a handful of pressed, AccurateRip-listed, single-disc albums. Missing
  and each one exercises different code: a **CD-R** or an obscure pressing (not in
  AccurateRip — the "no consensus to converge toward" path), a **multi-disc set**
  (`-c`, DISCNUMBER/totaldiscs), a **various-artists compilation** (per-track
  artist naming), a **genuinely damaged disc** (the read-speed ladder and the
  unresolved-track flagging, never once exercised), a disc with **CD-TEXT**, and a
  **pre-emphasis** disc.
- [ ] **The never-exercised list, which is joint with the fork and has not moved
  in four rounds:** `-x` on a real drive, C2 error reporting, `-f`, damaged media,
  CD-TEXT from a physical disc, a diagnosed abort, a non-zero `Read stalls:`.
  Nobody on either project has touched any of them, on any build.

**Not a blocker for any of it:** none of these makes `0.6.4` unsafe, and by S-14
none of them holds a release. They are what a **1.0** would be claiming stability
around, which is a different question from whether today's build is good.

## Open, from the b15 reachability sweep (2026-08-06)

- [ ] **Sweep the rest of `src/` for unreachable subsystems.** Two were found in one
  afternoon by asking *"does anything outside this package import it?"* — `uiscript/`
  (no menu item, no flag) and `rig_session.sh` (in `scripts/`, so absent from every
  built artifact). Neither was caught by a green suite, because a subsystem's own
  tests import it directly. Run the same question over every package and data file:
  `grep -rn '<pkg>' src/ --exclude-dir=<pkg>`, and for data, check
  `[tool.setuptools.package-data]` rather than the filesystem. Rule: `docs/testing.md`
  §5.ag.

- [ ] **Decide the `[Debugging]`-on-the-Goal-row question.** Still the maintainer's
  call and still unanswered: should the Goal label mention state the preset does not
  own (debug logging on, a test script set to autorun)? It means deciding which fields
  a label may speak for. Not an oversight — a design question held open deliberately.

- [ ] **Consider surfacing the `[plan]` block in the UI, not only the log.** It goes to
  the live log pane today, which is right during a rip but is not where someone decides
  whether to *start* one. A one-line summary beside the Start button ("Test & Copy: off
  — only AccurateRip misses re-read") would put it at the decision point. Deferred, not
  dropped: it needs a place in the layout that does not push the track grid around.

## Open, from round 7 laps 32-33

- [ ] **Implement `HANDSHAKE-CONCURRENT-WITH` when writing lap 35.** The rip laps are written
  blind and exchanged simultaneously, so lap 36 does *not* reply to lap 35 and a reader who
  assumes it does will conclude the fork ignored our findings. One optional header field naming
  the other half of the pair. **No version bump**: by the rule both sides agreed in lap 32/33, a
  change that alters what a gate must *refuse* bumps the version; an optional field does not — and
  v2 gates ignore unknown fields, which is what lets a proposal ship before the other side
  implements it (their §6a reasoning, third application).

  Verified rather than assumed, before proposing it: **a blind lap cannot close a round.**
  `close_blockers` requires `HANDSHAKE-PEER-VERDICT: GO`, and a blind lap can only transcribe the
  peer's *previous* verdict (HOLD → refused) or omit it (→ refused). And `round_status` reads each
  side's latest lap from its own directory, so a duplicated lap number cannot confuse the gate
  either. The collision risk is a human misreading the record, not a gate mis-deciding it.


- [ ] **Round 8 lap 1 — raise `PROTOCOL_VERSION` to 3, then bump the shared file.**
  Two steps in that order, agreed with the fork (their lap 32 §F/J1, our lap 33 §F/J1).
  Raising the constant first is backward-compatible (`declared <= implemented`), and doing
  it the other way round means whichever side declares 3 first has its file refused by the
  other — *including the file carrying the bump*. Neither side has raised it yet, on purpose.

- [ ] **Round 8 — cross-check `HANDSHAKE-SHARED-HASHES` against theirs.** We declare ours and
  verify them against our own tree; nobody compares the two sides yet. Needs the inbound file
  plumbed into `scripts/handshake.py`. Both sides shipped the declaration without the check and
  said so.

- [ ] **Round 8 — the three exit codes we named**, in the fork's queue: "the flag I sent does
  not exist in this build" first, then disc/drive-failure vs argument-refusal, then
  cancelled/signalled. Our side is the consumption: stop treating every non-zero as one thing.

- [ ] **Three CHANGELOG headings claim releases that were never tagged** — `0.5.16`, `0.2.0`,
  `0.0.1` — and the `0.5.16`/`0.5.17` compare links resolve to nothing. Found while fixing the
  same defect in `0.6.4b12` (which *was* this cycle's, and is fixed). These three predate the
  cycle; deciding what they should say needs their history, and guessing would be worse than
  leaving them. **Not a gate yet either**: a tag-vs-heading check needs tags in CI, and the
  `test` job checks out shallow without them, so it would need a workflow change to be honest
  rather than a skip.

- [ ] **Answer the fork's H3 question about a Platterpus-side sanitiser blind spot.** They
  found ASAN and UBSAN both blind to their argv overread. Our nearest equivalent of that false
  comfort is *"the parsers have a `hypothesis` never-raises property test, so malformed input is
  covered"* — which proves survival, not correctness of the value returned. Worth a real audit
  rather than the one example we volunteered.

## Next release — gated on the rig package

*(Absorbed the former `release-plan-next.md` on 2026-08-06. It was a separate
file for one day. A release plan **is** a task queue with an ordering constraint,
so its home was always here — keeping it outside meant a START-HERE reader saw the
backlog and not the thing gating it. CLAUDE.md Critical rule #7's fourth
obligation is what this merge implements.)*

**Status: waiting on the maintainer's rig package.** He is ripping now and will
send logs, cue sheets and the JSON report. Nothing releases until that lands and
its findings are folded in — his instruction, and the right call: *"you dont need
to release anything now, but plan to do this all to a new, at least beta, but
maybe more release, as soon as you have the full package. feel free to start now,
but you make more work."*

That last clause is the governing constraint. Work that his data could
**invalidate** waits. Work his data **cannot touch** can proceed. *The queue,
sorted by whether his data can invalidate it* below sorts on exactly that line.

### What is already on the branch

Pushed to `claude/session-omka9f`, all green (37 uiscript tests + the full suite,
lint and format clean):

| landed | what it was |
|---|---|
| **v0.6.4b11** | published pre-release: option-label convention, three screens that name the build, the derived `rip_goal`, dialog lifecycle logging |
| Settings scroll fix | `minimumSizeHint` was **739 × 971** — the dialog could not be shrunk *at all*, so OK/Cancel sat below the screen edge. Now 146 px, form scrolls, actions never do |
| uiscript pure layer | vocabulary, parser (never raises, fuzzed), transcript |
| uiscript runner | QTimer state machine; screenshot **plus a window manifest**, because `grab()` returns a valid pixmap for a dialog that was never shown |
| cyanrip passthrough | routed through `run_capture` — the app's own seam — and **sanitised**, after the maintainer's question found it bypassed the argv chokepoint |
| Critical rule #12 extension | bidirectional seam sanitation, institutionalised in `CLAUDE.md` and drafted for the fork |

### What the rig package unblocks

Each of these is **blocked on his data** and cannot be honestly finished without
it:

| needs the package | why |
|---|---|
| **The b11 verdict** | did the stall warning stay quiet on a healthy re-read? Did the ETA hold? Only the rip says. |
| **`eta_trace.samples[].state`** | b8 had two holes totalling ~16 min landing exactly on the wrong minutes. A gap in b11's trace means the fix is incomplete — this is the first field to open. |
| **`settings.rip_goal_stored`** | new in schema v23. Present ⇒ his `config.toml`'s label disagreed with its own fields. |
| **The picker question** | `dialog presented: ReleasePickerDialog` in `log.txt`, or its absence. The one thing b10's log could not answer. |
| **Handshake round 7 close** | the cue-sheet pre-gap check on tracks 3/6/11/12 is the only change in the fork's pin no drive has run. |
| **Whether the ETA needs work at all** | median −23 min on b8, deliberately untouched pending this trace. |

### The queue, sorted by whether his data can invalidate it

#### THE FIRST DELIVERABLE, and what it forces

His directive: *"the first test should be giving copying and pasting in a script
that tests every paramter/arguement, and give back a result. then we should be
able to determine if all is reaching platterpus and cyanrip, then we can go from
there."*

**Right instinct — plumbing before behaviour.** Before asking whether a setting
*works*, ask whether the script can *reach* it at all. A reachability sweep is
the cheapest possible first test and it fails loudly rather than subtly.

**But it cannot be written today, and the reason is our own defect:** `set` and
`expect` — the two verbs a "test every parameter" script is made of — are among
the **13 of 25 that are advertised and unimplemented**. Handing him that script
now would hand him a batch that fails on every line. So the two "safe to do now"
items below are not merely safe, they are **prerequisites of the first
deliverable**, and the order is forced:

> `set`/`expect` on Config field names → the remaining verbs → **generate** the
> coverage script → he pastes it → we read the result.

**The design decision that matters: the script is GENERATED, not hand-written.**
A hand-written "tests every parameter" script is wrong the day a field is added,
and wrong *silently* — it would still pass, just over a smaller surface, which is
the completeness-decay shape `docs/testing.md` §5.af describes. So a
`scripts/emit_uiscript_coverage.py` derives it from the **`Config` dataclass
fields** plus the **verb table**, exactly as `scripts/emit_dependency_contract.py`
already derives our half of the cyanrip contract. Then:

- every parameter is covered **by construction**, not by anyone's diligence;
- a new `Config` field appears in the next generated script automatically;
- and a **completeness test** asserts the generated script names every editable
  field, so the claim "tests every parameter" is checked rather than asserted.

**What the result must distinguish**, because "it reached Platterpus" and "it
reached cyanrip" are different claims and the script has to separate them:

| outcome | means |
|---|---|
| `set` FAILs | the field is not addressable — a **Platterpus** plumbing gap |
| `set` passes, `expect` FAILs | it was accepted and did not stick — a Platterpus **state** bug |
| both pass, argv lacks the flag | reached Platterpus, **not** cyanrip — the interesting one |
| both pass, argv carries it | full path confirmed end to end |

That last pair is why the script pairs every `set` with a `cyanrip`-side check
rather than stopping at the GUI: **reaching the app is not reaching the ripper**,
and only the argv proves the second.

#### Safe to do now — his data cannot change these

1. **[ ] The 13 unimplemented verbs.** `verbs.py` advertises 25, `runner.py`
   implements 12. This is `docs/testing.md` §5.p committed by the hand that wrote
   the rule. **Plus the one-line sweep** asserting the two sets agree, which is
   what stops the next one.
2. **[ ] `set`/`expect` keyed on `Config` field names, not row labels.** Seven form
   rows have the label `""`, five of them interactive — a label namespace cannot
   reach five real switches. Generalise `settings_dialog.py:700`'s existing
   `_validated_widgets` registry so the resolver, the validation renderer and the
   completeness test share one source. Traps recorded below in *P0 — `set`/`expect`
   must key on Config field names*: `secure_rerip_dynamic` **inverted**,
   `update_channel` a bool view of a string, U+00D7 and U+2026 in labels, three
   substring collisions, disabled widgets must fail **loudly** rather than no-op.
3. **[ ] The return-path sanitiser and the plain-text sweep.** `setTextFormat` has
   **zero** hits across the UI package, so every widget is on `Qt::AutoText`,
   which auto-detects HTML. A MusicBrainz title containing `<` is swallowed in an
   error dialog and the user never learns text went missing. Sweep, don't
   spot-fix.
4. **[ ] The console dialog**, gated behind two separate Settings toggles (show the
   console; allow unsafe verbs), plus the Tools menu entry.
5. **[ ] Handshake lap 28.** Independent of the rip *except* for the pin verdict —
   draft everything else now: withdraw the stale HOLD (their flag table arrived;
   `_MAX_TABLE_LAG` is 0), correct the recommendation of a pin our own
   `fork_source.py` lists as superseded, raise the three-sends-under-one-lap-number
   protocol breach, and attach the §S seam-sanitation clause already drafted.

#### Wait for the package

6. **[ ]** Read the artifacts; fold every finding into the queue before cutting anything.
7. **[ ]** The `ui_script` block in the rip JSON, **under the 25 MB ceiling** — his
   package tells us how much headroom a real report actually leaves.
8. **[ ]** The pin verdict in lap 28, and whether round 7 can close.
9. **[ ]** Whatever the rip itself surfaces.

#### Last

10. **[ ] One release.** Version decided by what lands: another beta if the package
    raises anything unsettled, or the **stable v0.6.4** if round 7 closes on a
    bilateral GO. `scripts/handshake.py --release-gate` decides that, not a
    preference — a stable release is blocked while a round is open, and that is
    the deviation policy.
11. **[ ] The single batch script**, written against a vocabulary where every verb
    works. Writing it before item 1 would hand him a script that fails on him.

### The release gate — what must be true

- Full suite green with the sentinel at `0`; coverage ≥ 91 %; ruff + mypy clean.
- `pytest tests/test_no_stale_version_claims.py` and `tests/test_doc_version_stamps.py`.
- `scripts/handshake.py --release-gate` — `--prerelease` permits a beta with the
  round open; **stable requires bilateral GO**.
- Every P0 in this file either fixed or explicitly deferred **in writing**.
- The batch script exercised against the real vocabulary, not against the table.

### The maintainer's stated intent for the release

His heads-up, verbatim: *"after i upload all the new logs and documents, plan to
take those and what we have here, and make a new beta version we can do another
round of handshakes with the cyanrip app, so we can try again."*

That settles the version question *Last* left open, and it settles it
**downward**: the next release is a **beta**, deliberately, because its job is to
be the artifact a *new handshake round* is run against. A stable v0.6.4 would be
the wrong shape for that even if round 7 closed — you cannot open a round on a
build whose purpose is to be final.

So the sequence is: **package → findings → beta → round 8**, and the beta is
named in the round-8 outbound file as the app version the round approves against
(Critical rule #12: a round approves a pin *for a named app version*, and two
artifacts from one ripper under different app versions are not interchangeable
evidence).

Two consequences worth stating now:

- **Round 7 gets closed or explicitly carried, not left ambiguous.** Lap 28 is
  still owed regardless — our sent lap 27 declares a HOLD whose stated reason has
  evaporated and recommends a pin our own `fork_source.py` lists as superseded.
  Opening round 8 on top of an un-corrected round 7 would compound that.
- **`docs/seam-rules.md` ships with the beta**, so round 8 can cite
  `SEAM-RULES-VERSION: 1` rather than re-argue it.

### Round 8 — what goes to the fork, and what the maintainer uploads

His instruction: *"give a new handshake file for cyanrip include all wel've said
and learned. make sure they are informed to follow our new formats and standards,
and give them any new information they need to improve or fix based on what we
learned/have seen. and make sure they update their stuff and give us back
something similar."*

**The round-8 outbound package is five things, sent together:**

| # | what | why it must be in the same round |
|---|---|---|
| 1 | **`docs/seam-rules.md` v4** | the twelve tagged rules. Adopted as a file, not paraphrased — a restatement is a second spec that can drift |
| 2 | **`docs/seam-commands.md`** | the one table. Our column filled, theirs `?`. Their half is the ask |
| 3 | **The round-8 verification file** | withdraws lap 27's stale HOLD, corrects our recommendation of a superseded pin, raises the three-sends-under-one-lap-number breach, and carries §S/§S5a/§S5b/§S5c |
| 4 | **The rip artifacts** | evidence *about their binary*, which is the only thing that can settle the cue fix and close round 7 |
| 5 | **Our own defect list** | what we found in ourselves this cycle. A contract argued from a hole you just found in yourself carries more weight than one argued from a clean position |

**What we ask back, explicitly**: their half of the command table, their exit-code
grading with the `generic` list, their three S-11 numbers and their regression-test
list, and confirmation the rules landed in their `CLAUDE.md` — so round 9 can
*cite* rather than re-argue.

#### The upload order, and why it is not "whenever"

The maintainer offered: *"i can also upload all the log and other files there if
helpful, just let me know what to do when you are ready."* The answer is **yes,
but after we have read them, not before**, and the reason is specific:

1. **We read the artifacts first.** They may change what the round-8 file says —
   a wrong pre-gap result sends their cue fix back and the file's verdict inverts.
   A file written before we looked would need retracting, and this protocol has
   already spent a round on a retraction.
2. **Then everything goes at once.** Analysis and evidence arriving together
   means they can check our reading against the same bytes. Evidence without the
   reading invites them to re-derive it; the reading without the evidence asks
   them to take it on trust. Both have failed here before.
3. **The artifacts are named in the file's header**, so a later reader can tell
   which log settled which claim — the *answer it from the artifact, and name
   which artifact* rule.

So: **send nothing to the fork yet.** When the package is read and round 8 is
written, the upload is one action with a stated manifest.

### What could change this plan

Stated so that a later reader can tell a revised plan from a forgotten one — this
is the framing that makes the block above a *plan* rather than a pile of
backlog rows, so it stays a named subsection wherever this content lives:

- **A gap in `eta_trace` during the re-reads** promotes the ETA from "deliberately
  untouched" to a release blocker.
- **A missing `dialog presented:` line** means the picker was created and never
  shown — a different and more serious bug than the logging gap already fixed.
- **A wrong pre-gap result** sends the fork's cue fix back and round 7 stays open,
  which forces a beta rather than a stable.
- **A report near 25 MB** changes the `ui_script` embedding from "include the
  transcript" to "reference it and embed a digest".

---

## P0 — v1 release

### ⭐ First-rip proof — raised by the maintainer 2026-07-30, needs a decision before work starts

> *"this is great for already verified things, but this is done by people running EAC, more
> confirmation helps confidence, but we need to be able to confidently be able to be the
> gold standard first burn proof as well. until this this will not be a serious product."*

**The gap is real and correctly identified.** Every strong claim the app can make today is
*borrowed*: AccurateRip and CTDB both answer "do other people's rips agree with yours",
so a disc nobody has submitted — a CD-R, a promo, an obscure pressing — gets grey
"couldn't confirm" and the user is left with a Copy CRC that only proves FLAC encoded
whatever was read. For a first rip the app currently has no verdict of its own.

**What is physically achievable, stated honestly.** With one drive and no database the
only available evidence is **reproducibility plus error accounting**: N independent reads
returning identical bytes, with cache defeat *measured*, at a *confirmed* offset, and zero
uncorrected paranoia events. That is exactly what EAC's Test & Copy is, and it is a strong
claim — but it is categorically weaker than AccurateRip in one specific way that must
never be glossed: **it cannot detect a systematic misread**, a drive that returns the same
wrong bytes every time. Only a *second drive* breaks that, because it is the only way to
vary the thing being tested. Any "gold standard" wording has to respect that boundary or
it is the same borrowed confidence in a new costume.

Four candidate pieces, cheapest first. **None started — the defaults question below is the
maintainer's call, not mine:**

1. **A first-rip verdict tier.** Today "not in AccurateRip" collapses to grey. Instead
   report what we *can* prove, as its own named tier with its own colour: reads agreed
   (N of N), cache defeat measured, offset confirmed by two sources, paranoia counts
   clean, C2 status. All five facts are already collected — this is presentation, and it
   is the highest value for the least risk.
2. **Test & Copy on by default when AccurateRip has nothing.** The behaviour change that
   makes tier 1 mean something: if no database can vouch for the disc, earn the proof
   locally instead of shrugging. Costs a second full read (roughly doubles rip time) on
   exactly the discs where it matters. ***Needs sign-off: is doubling the rip time
   acceptable for an unknown disc?***
3. **Cross-drive verification, as an explicit feature.** Rip in drive A, rip in drive B,
   `--compare` the reports; agreement at each drive's own offset is the strongest evidence
   a single owner can produce, and it is the only one that survives a systematic misread.
   `--compare` already exists; this is a guided flow plus a verdict, not new machinery.
4. **Submit to CTDB — become the datum rather than only consuming it.** Doesn't prove
   *this* rip, but it is what "gold standard" means socially: the next person to rip the
   disc can verify against us. AccurateRip submission is confirmed impossible from Linux;
   CTDB submission needs investigation (the CUETools ecosystem, `ctdb-cli` — see P1 item
   6, which is already on the list for repair rather than submission).

**Also raised by the same run, and also a decision rather than a fix:** typed titles land
in the tags and the `.cue` but not in the **filenames** (`03 - Track 03.flac`, not
`03 - three3.flac`) on the unknown-disc path, because cyanrip names files from the
placeholders it was given and Platterpus tags over the top afterwards. Sheet item **D4**.

### Foundation

- [x] T01 — Repo scaffolding
      Acceptance: `pyproject.toml`, `.gitignore`, `src/platterpus/__init__.py` (with `__version__`), `src/platterpus/__main__.py` (calls `app.main`), empty `tests/`, empty `build/` directory exist. `python -m platterpus` runs and exits cleanly with a placeholder message.
      Phase: P0
      Done: pyproject.toml uses setuptools src-layout; `app.py` carries a placeholder `main()` so the entry point is real. Verified `PYTHONPATH=src python -m platterpus` exits 0 with the placeholder message on Python 3.11.15.

- [x] T02 — Paths module (`paths.py`)
      Acceptance: module-level constants `CONFIG_PATH`, `LOG_DIR`, `WHIPPER_CONFIG_PATH`, `WHIPPER_BINARY_DEFAULT` populated from XDG env vars with sane fallbacks. Used by `config.py` and `logging_setup.py`.
      Phase: P0
      Done: paths.py exports the constants above plus `APP_NAME`, `CONFIG_DIR`, `LOG_PATH`. Honors `XDG_CONFIG_HOME` and `XDG_DATA_HOME` when set; falls back to `~/.config` and `~/.local/share`. Verified: setting XDG vars to `/tmp/...` produces matching `CONFIG_PATH` and `LOG_PATH`. Note: T02 and T03 were swapped from the original ordering (logging depended on paths), so this is the original T03.

- [x] T03 — Logging setup module (`logging_setup.py`)
      Acceptance: importing and calling `configure_logging()` once produces a rotating file at `~/.local/share/platterpus/log.txt` plus a console handler at INFO. `logging.getLogger(__name__)` in any module writes to both.
      Phase: P0
      Done: `configure_logging()` is idempotent (sentinel attr on root logger); file handler captures DEBUG+, console handler captures INFO+ (configurable). Rotation: 5 backups of 1 MiB. Verified: three calls produce exactly two handlers, INFO+DEBUG land in the file, only INFO on stderr.

- [x] T04 — TOML config module (`config.py`)
      Acceptance: `load_config()` returns the parsed TOML as a typed dataclass, creating the file with defaults if missing. `save_config(cfg)` atomically writes (temp + rename). Schema version embedded. Unit-tested in `tests/test_config.py`.
      Phase: P0
      Done: `Config` dataclass with output dirs, rip templates, tool paths, read_offset, auto_launch_picard, and schema_version. `load()` and `save()` (renamed from `load_config`/`save_config` for brevity — caller writes `config.load()`). Atomic save via temp + os.replace. Unknown keys dropped with warning. 4 unit tests pass (defaults creation, roundtrip, atomic temp cleanup, unknown-key tolerance).

### Dependency self-management subsystem (brief P0 #11)

- [x] T05 — Version-string parsing utility (`deps/version.py`)
      Acceptance: `parse_version(text, pattern)` and `meets_minimum(version, minimum)` exist. Unit-tested.
      Phase: P0
      Done: `parse_version()` uses a named-group regex (default matches `MAJOR.MINOR[.PATCH]`) and returns an int tuple or None. `meets_minimum()` pads short tuples with zeros so `(1, 2)` >= `(1, 2, 0)`. 12 tests pass including the "0.10.0" double-digit trap. Created `src/platterpus/deps/__init__.py` to make the package importable.

- [x] T06 — Probe functions (`deps/checks.py`)
      Acceptance: `check_whipper()`, `check_metaflac()`, `check_libdiscid()`, `check_picard_flatpak()`, `check_python_pkg(name)` each return a `ProbeResult(present, version, location)`. No side effects.
      Phase: P0
      Done: All five probes implemented. `ProbeResult` is a frozen dataclass with `present`, `version`, `location`, `raw_output`. Subprocess probes use a 10s timeout. `check_libdiscid()` uses ctypes (no subprocess). 10 unit tests pass via monkeypatched subprocess.run/shutil.which.

- [x] T07 — DependencySpec registry (`deps/registry.py`)
      Acceptance: `SPECS: list[DependencySpec]` declaratively lists all v1 deps (whipper, metaflac, libdiscid, musicbrainzngs, Picard). Each spec names probe, min_version, tier preference, install command, and tier-(c) search string.
      Phase: P0
      Done: 4 specs registered: whipper (manual, 0.10.0+), metaflac (manual, 1.3.0+), Picard (auto via Flatpak with queued/manual fallbacks), musicbrainzngs (manual reinstall path). `libdiscid` deferred to T32 per KDD-06; when the smoke test shows we need it, one new entry lands here and nothing else changes. `Tier` is an enum with AUTO/QUEUED/MANUAL; `DependencySpec` is frozen with an optional `fallback_tiers` tuple for cascade-on-failure.

- [x] T08 — Resolver classes (`deps/resolvers.py`)
      Acceptance: `AutoInstaller`, `QueuedInstaller`, `ManualPrompt` exist with a common `resolve(specs)` shape. AutoInstaller runs pipx and `flatpak install --user`. QueuedInstaller and ManualPrompt drive UI dialogs (defer wiring until T18/T19 land).
      Phase: P0
      Done: All three resolvers share `resolve(items: list[MissingItem]) -> list[InstallResult]`. AutoInstaller runs the spec's `install_command` via subprocess after a consent callback (default refuses). QueuedInstaller reuses AutoInstaller's machinery for the actual install — the dialog callback just chooses which items to install. ManualPrompt invokes a per-item callback and returns `success=False` for every item. All callbacks have logging-only defaults; T18/T19 will inject the Qt dialogs. 8 unit tests pass. Acceptance criterion corrected: dialog wiring is T18 (manual_install) and T19 (pending_installs), not T15/T16.

- [x] T09 — DependencyManager orchestrator (`deps/manager.py`)
      Acceptance: `DependencyManager.check_all()` walks the registry, classifies, dispatches to resolvers, returns a `DependencyReport`. Idempotent. Unit-tested with mocked probes in `tests/test_dependency_manager.py`.
      Phase: P0
      Done: `DependencyManager` accepts injected resolvers and an optional spec list (defaults to `registry.SPECS`). `check_all()` is pure (no resolution); `resolve_missing(report)` dispatches by tier and cascades to `spec.fallback_tiers` on failure. `DependencyReport.all_resolved` summarizes status. 9 unit tests pass, including a no-args construction that exercises the real registry against the live system. Test file is `tests/test_deps_manager.py` (kept consistent with the test naming pattern `test_deps_*.py`).

### Parsers

- [x] T10 — Drive list parser (`parsers/drive_list.py`)
      Acceptance: `parse_drive_list(stdout)` returns `list[DriveDescriptor]`. Fixture-driven test with sample `whipper drive list` output.
      Phase: P0
      Done: `parse_drive_list()` returns `list[DriveDescriptor]` with `device`, `vendor`, `model`, `release`, `read_offset` (None if unconfigured), `cache_defeat` (None if unknown). Format verified against whipper-team/whipper master `command/drive.py`. 4 fixture files in `tests/fixtures/`; 7 tests pass. Note: T10-T15 reordered so parsers come before adapters — the adapter at T13 imports from parsers, so swapping made the dependency order match the execution order.

- [x] T11 — CD info parser (`parsers/cd_info.py`)
      Acceptance: `parse_cd_info(stdout)` returns `DiscInfo`. Fixture-driven test.
      Phase: P0
      Done: `DiscInfo(cddb_disc_id, musicbrainz_disc_id, musicbrainz_submit_url)`; missing fields default to empty strings. Three regexes (with named groups) match the inconsistent "CDDB disc id:" / "MusicBrainz disc id" (no colon!) / "MusicBrainz lookup URL" lines whipper emits per master `command/cd.py`. Tolerates surrounding log noise. 2 fixture files, 4 tests pass.

- [x] T12 — Rip log parser (`parsers/rip_log.py`)
      Acceptance: `parse_rip_log(text)` returns a `RipLog` with per-track CRCs, AccurateRip confidence, error counts. Fixture-driven test with at least one real whipper `.log`.
      Phase: P0
      Done: State-machine parser produces `RipLog{log_creator, creation_date, ripping_info, tracks, accuraterip_summary, health_status, sha256_hash}`. Each `TrackResult` holds peak_level, pre_emphasis, extraction_speed/quality, test/copy CRCs, status, and AR v1/v2 results. New `RippingInfo` sub-record (drive, extraction_engine, defeat_audio_cache, read_offset_correction, overread_lead_out, gap_detection, cd_r_detected) mirrors EAC's archival header per docs/eac-parity.md. **Primary fixture is the real whipper log from upstream's own test suite** (`tests/fixtures/rip_log_real_whipper_0_7.log`). My initial hand-authored fixture had a wrong track-header format and was deleted. EAC reference log (`rip_log_eac_reference.log`) stored for archival comparison only; not parsed. 18 tests pass.

### Adapters

- [x] T13 — WhipperBackend ABC + host-exported impl (`adapters/whipper_backend.py`)
      Acceptance: `WhipperBackend` ABC with all five methods from PLANNING.md §5. `WhipperHostExportedImpl` shells out to `~/.local/bin/whipper`. Tested with fixture-driven mocks in `tests/test_whipper_backend.py`.
      Phase: P0
      Done: `WhipperBackend` ABC with four methods (`list_drives`, `disc_info`, `rip`, `version`) — PLANNING.md §5 listed "five methods" inclusive of the rip-returned `RipHandle`'s methods, which now live on the handle class. `WhipperHostExportedImpl` accepts `binary_path` and optional `working_dir`, shells out to whipper, parses via `parsers.drive_list` / `parsers.cd_info`. `RipHandle` wraps the Popen, exposes `log_lines()` (generator), `wait()`, `cancel()` (SIGTERM-then-SIGKILL), and `returncode`. `WhipperError` carries the last error line for the GUI. 13 tests pass: argv construction, `--unknown` flag, working_dir presence/absence, log-line streaming, cancel cascade, post-exit cancel safety, ABC discipline, FileNotFoundError + TimeoutExpired handling.

- [x] T14 — MusicBrainzClient ABC + ngs impl (`adapters/musicbrainz_client.py`)
      Acceptance: ABC per PLANNING.md §6. `MusicBrainzNgsImpl` wraps `musicbrainzngs`. `set_user_agent` invoked at construction. Exceptions reraised as `MusicBrainzQueryError`. Tested with `musicbrainzngs` mocked.
      Phase: P0
      Done: ABC + impl with 4 methods (`releases_by_disc_id`, `releases_by_toc`, `release_by_mbid`, `set_user_agent`). Data types: `TocSignature`, `ReleaseSummary`, `TrackSummary`, `ReleaseDetail` — all frozen dataclasses. `MusicBrainzQueryError` wraps `musicbrainzngs.WebServiceError`; 404 responses on disc-id/TOC queries are translated to `[]` (since "no match" isn't an error from the picker UI's perspective). MB response shape helpers isolated as private functions so a future `RequestsJsonImpl` against MB's JSON endpoint can produce the same dataclasses. 13 tests pass, including artist-credit rendering (which interleaves dicts and joining strings like " feat. ").

- [x] T15 — Metaflac adapter (`adapters/metaflac.py`)
      Acceptance: `MetaflacAdapter.write_tags(flac_path, tags)` and `.read_tags(flac_path)` work via the `metaflac` CLI. Used by the unknown-album flow.
      Phase: P0
      Done: `MetaflacAdapter` constructor takes a `binary_name` (default "metaflac"; user can override via config). `read_tags()` uses `--export-tags-to=-` and parses `KEY=VALUE` lines (duplicate keys → last value wins, matching metaflac's own preference). `write_tags()` batches `--remove-tag=K` followed by `--set-tag=K=V` so existing values are replaced not duplicated. Empty dict is a no-op. `MetaflacError` carries the last stderr line. 9 unit tests cover all three methods plus FileNotFoundError, TimeoutExpired, and custom binary paths.

### Workers

- [x] T16 — Rip worker (`workers/rip_worker.py`)
      Acceptance: `RipWorker(QObject)` owns the rip subprocess; emits `log_line`, `progress`, `finished`, `error`. `.cancel()` terminates cleanly.
      Phase: P0
      Done: `RipWorker` QObject + frozen `RipParameters` dataclass. Signals: `log_line(str)`, `progress(int track, float percent)`, `finished(bool success, str log_path)`, `error(str)`. `start_rip` slot drives `WhipperBackend.rip()`, iterates `RipHandle.log_lines()`, emits progress when defensive regex matches. `cancel` slot is safe to call before start (just sets the flag) and after (forwards to handle). `_find_log_path()` locates the most recent `.log` under `output_dir` for the finished signal. 12 unit tests pass with a fake backend + handle. Progress regex deliberately permissive — T32 smoke test will tell us whether it needs tightening for real whipper output.

- [x] T17 — MusicBrainz worker (`workers/mb_worker.py`)
      Acceptance: `MusicBrainzWorker(QObject)` runs `MusicBrainzClient` calls on a background `QThread`; emits `releases_returned` or `error`.
      Phase: P0
      Done: `MusicBrainzWorker` exposes three slots — `lookup_disc_id(str)`, `lookup_toc(TocSignature)`, `fetch_release(str mbid)` — emitting `releases_returned(list)` for multi-result queries, `release_returned(object)` for the single-release fetch (using `object` so PySide doesn't require an explicit type registration for the ReleaseDetail dataclass), and `error(str)` on any `MusicBrainzQueryError`. One worker handles all three query types; slot serialization ensures queries don't interleave. 7 unit tests pass with a fake MusicBrainzClient covering success, error, and empty-result paths for all three slots.

### UI — dialogs first, then the main window assembles them

- [x] T18 — Manual install dialog (`ui/dialogs/manual_install.py`)
      Acceptance: `ManualInstallDialog` shows missing item, min version, reason, and a copyable read-only QLineEdit with the search string. Copy is primary, Close is secondary.
      Phase: P0
      Done: Modal `ManualInstallDialog(spec, probe)` with title "Install required: {name}", form rows for required version / current state / why-manual, a read-only QLineEdit carrying the search string, and a button box with Copy (AcceptRole, default) + Close (RejectRole). Copy writes to the system clipboard and briefly flips the button label to "Copied!" before resetting via QTimer. Display strings handle the "any version" floor `(0,0,0)` and the "installed but version unknown" probe state. 12 unit tests pass with the QApplication fixture from `tests/conftest.py` (added this commit, anticipates T30). Test environment runs with QT_QPA_PLATFORM=offscreen so a real display isn't required.

- [x] T19 — Pending installs dialog (`ui/dialogs/pending_installs.py`)
      Acceptance: `PendingInstallsDialog` displays a checkbox list with per-item progress; "Install selected" triggers the loop. Backed by `QueuedInstaller`.
      Phase: P0
      Done: Modal `PendingInstallsDialog(items)` renders one row per item (checkbox + name + min-version hint + status label). Default-checked so a "one click installs everything" flow works. `install_requested` signal fires on Install Selected click (dialog stays open during install). Caller drives the install loop and updates per-row state via `mark_in_progress(dep_id)` / `mark_result(dep_id, success, message)` (failure messages truncate to 60 chars to keep the dialog compact). `set_install_phase_active(True)` locks down the picker during installs; `show_close_button()` (idempotent) swaps the bottom row to a single Close button for dismissal. 19 unit tests cover construction, selection, signal emission, status updates, long-message truncation, lockdown, and the close-button swap.

- [x] T20 — Settings dialog (`ui/settings_dialog.py`)
      Acceptance: fields for output dir, working dir, track template, disc template, read offset, whipper/metaflac paths, auto-launch-Picard toggle. Writes through `config.py`. Includes a "Check dependencies" button that re-runs `DependencyManager.check_all()`.
      Phase: P0
      Done: Modal `SettingsDialog(config)` is a pure view — it doesn't read or write the config file. Form rows for all eight Config attributes (paths get a Browse… button; read_offset is a bounded QSpinBox; auto-launch-Picard is a checkbox). `to_config()` builds a new `Config` reflecting widget state and preserves the incoming `schema_version` (the dialog doesn't model migration). "Check dependencies" button emits `check_dependencies_requested` signal — caller wires it to `DependencyManager.check_all()`. Dialog stays open after the signal so the user can see results in a separate report and tweak settings. 11 unit tests pass. Also consolidated worker-test fixtures onto `qapp` (from conftest.py) since a process-wide QCoreApplication blocks later UI tests from creating QApplication.

- [x] T21 — Drive picker widget (`ui/drive_picker.py`)
      Acceptance: combo box populated from `WhipperBackend.list_drives()`. Emits `drive_changed(device_path)`.
      Phase: P0
      Done: `DrivePicker(backend)` is a horizontal panel: label + QComboBox + Refresh button. Construction does NOT call list_drives — the caller decides when (avoids surprise subprocess calls during widget construction). `refresh()` rebuilds the combo, preserves the prior selection if the same device is still present, falls back to the first drive otherwise. Errors from the backend show as an "(error: …)" placeholder rather than crashing — user can fix the path in Settings and refresh again. `drive_changed` emits exactly once per real selection change (signal-blocked during repopulation). 10 unit tests pass.

- [x] T22 — Disc info panel (`ui/disc_info_panel.py`)
      Acceptance: read-only panel showing TOC, MB match status, AccurateRip availability. Updates on `drive_changed`.
      Phase: P0
      Done: `DiscInfoPanel` is a pure view with five form rows: Drive, MusicBrainz disc ID, CDDB disc ID, MusicBrainz match, AccurateRip. Setter methods (`set_drive`, `set_disc_info_loading`, `set_disc_info`, `set_disc_info_error`, `set_mb_loading`, `set_mb_matches`, `set_mb_error`) — the main window orchestrates the disc_info + MB lookup workers and feeds results in. `set_drive()` clears all disc-derived fields so switching drives never leaks stale data. Value labels are mouse-selectable so users can copy disc IDs into Picard or a browser. Acceptance differs from spec in two ways flagged for review: (1) TOC isn't in `whipper cd info` output (only in the post-rip log), so the panel can't show it pre-rip — TOC display will appear in rip-progress (T26); (2) AccurateRip availability is also only checked during rip, so this panel shows a "verified during rip" placeholder and the actual results appear in T26. 15 unit tests pass.

- [x] T23 — Release picker dialog (`ui/release_picker.py`)
      Acceptance: `ReleasePickerDialog` lists MB release candidates; returns the chosen MBID. Substitutes for whipper's TTY prompt (Critical Rule #5).
      Phase: P0
      Done: Modal `ReleasePickerDialog(releases)` displays a 9-column QTableWidget (Title, Artist, Year, Country, Label, Catalog #, Tracks, Format, Notes). Row-level single selection, no in-place editing. Title and Artist columns stretch; the rest fit content. Row 0 is selected by default so a quick Enter accepts the top candidate. Double-click on a row also accepts (matches OS picker convention). `selected_mbid()` and `selected_release()` are the readback API. Empty release list is supported and returns None for both. 15 unit tests cover construction, row count, column mapping (each ReleaseSummary attribute → correct cell), missing-field rendering, non-editable cells, default selection, MBID readback, OK/Cancel/double-click acceptance paths.

- [x] T24 — Track table widget (`ui/track_table.py`)
      Acceptance: editable per-track `QTableView` with custom model. Album-level fields above the table. Validates before allowing rip start.
      Phase: P0
      Done: Composite widget with three album-level QLineEdits (artist/title/year) above a QTableView. Custom `TrackTableModel(QAbstractTableModel)` exposes 4 columns (#, Title, Artist, Length); Title and Artist are editable in-place, # and Length are read-only. Track length renders as MM:SS. `set_release(detail)` populates from MusicBrainz; `album_metadata()` and `tracks()` read back user edits (TrackSummary is frozen, so edits go through `dataclasses.replace`). `validate()` returns `(ok, message)` after checking that album artist/title aren't blank, at least one track exists, and every track has a title. `AlbumMetadata` frozen dataclass exposes the album-level edits. 22 unit tests pass (model behavior, editability flags, length formatting, set/clear/edit roundtrips, all four validate failure paths).

- [x] T25 — Rip controls widget (`ui/rip_controls.py`)
      Acceptance: Start / Cancel buttons. On Start, assembles rip parameters and emits `rip_requested(params)`.
      Phase: P0
      Done: `RipControls(config)` exposes Start + Cancel buttons. Three setter slots (`set_drive`, `set_release_id`, `set_unknown_mode`) accept state pushed in from the main window; `set_rip_active(bool)` toggles button enablement during a rip. Start enables when drive + release_id are present (or just drive in unknown mode). On Start click, assembles a `RipParameters` from current state + the injected `Config` (output_dir, templates) and emits `rip_requested(params)`. On Cancel click, emits `cancel_requested()`. 10 unit tests cover initial disabled state, enablement rules (with/without release_id, unknown mode, no drive), rip-active toggling, parameter assembly, unknown-flag passthrough, cancel signal, and state-clearing.

- [x] T26 — Rip progress widget (`ui/rip_progress.py`)
      Acceptance: live whipper stdout pane + per-track AccurateRip results table populated when the rip finishes + "View log" button.
      Phase: P0
      Done: Stacked vertical panel — status label + QProgressBar (0-100), streaming read-only QPlainTextEdit (capped at 10k scrollback lines so a long rip can't blow memory), AccurateRip results QTableWidget (5 cols: #, Title, Status, AR v1, AR v2), and "View log" button. Methods: `clear()`, `append_log_line(line)`, `set_progress(track, percent)`, `set_status(text)`, `set_rip_log(RipLog)`, `set_log_path(path|None)`. AR cells render as "OK (N)" / "not in DB" / "—" based on result+confidence. View Log button opens the log via `QDesktopServices.openUrl` (injectable for tests). 16 unit tests pass.

- [x] T27 — Unknown album helper (`ui/unknown_album.py`)
      Acceptance: triggers `--unknown` rip, applies placeholder tags via `MetaflacAdapter`, optionally invokes `flatpak run org.musicbrainz.Picard`.
      Phase: P0
      Done: Three pieces — `UnknownAlbumDialog(auto_launch_picard_default)` modal confirmation with a Picard toggle, `apply_placeholder_tags(metaflac, flac_files)` applying `Track NN` / Unknown Artist / Unknown Album / TRACKNUMBER per file (returns successes; individual failures logged but don't abort the batch), `launch_picard_for(folder)` running `flatpak run org.musicbrainz.Picard <folder>` as a detached subprocess (returns False on FileNotFoundError or OSError so the main window can surface a hint to install Picard). The actual `--unknown` rip is kicked off by the main window via `RipControls.set_unknown_mode(True)` + Start; this module is only the dialog + post-rip helpers. 11 unit tests pass.

- [x] T28 — Main window (`ui/main_window.py`)
      Acceptance: `MainWindow` lays out drive picker → disc info → track table → rip controls → progress. Menu: Settings, Check Dependencies, Quit. Wires worker signals into widget slots.
      Phase: P0
      Done: `MainWindow(config, backend, mb_client, metaflac, dependency_manager, save_config=None)` composes the entire GUI. Layout: drive picker → disc info → track table → rip controls → progress in a QVBoxLayout. Menu bar: File→Quit, Tools→Settings…, Tools→Check dependencies…. One persistent QThread holds the MusicBrainzWorker for the window's lifetime; each rip spawns a new QThread/RipWorker that auto-cleans on finish. Drive change triggers `backend.disc_info()` (sync) → panel update → MB worker `lookup_disc_id` → on result, single match fetches detail, multiple opens `ReleasePickerDialog`. Validation gate on rip start (`TrackTable.validate()`) blocks invalid metadata in non-unknown mode. Settings dialog wires its "Check dependencies" signal back to the main window's `_on_check_dependencies` so both entry points use the same code. The dep-check builds a fresh DependencyManager with GUI-backed resolvers (`QMessageBox.question` for auto-consent, `PendingInstallsDialog` for tier-b, `ManualInstallDialog` for tier-c) and runs `check_all` + `resolve_missing`. closeEvent tears down the MB thread and cancels any in-progress rip. Rip log is parsed and rendered into `RipProgress` after the rip finishes. 10 integration-flavored tests pass.

- [x] T29 — App entry point + startup sequence (`app.py`, `__main__.py`)
      Acceptance: `app.main()` builds QApplication, configures logging, runs `DependencyManager.check_all()` (showing any install dialogs first), then constructs and shows MainWindow.
      Phase: P0
      Done: `app.main(argv)` parses `--version` via argparse, configures logging, loads config, constructs QApplication (with name/version/org for QSettings), instantiates all adapter layers (`WhipperHostExportedImpl`, `MusicBrainzNgsImpl`, `MetaflacAdapter`, `DependencyManager`), creates the `MainWindow`, runs `window.run_dependency_check(show_summary=False)` for the launch-time check (silent when nothing's missing; modal dialogs surface for anything that needs attention), shows the window, and calls `refresh_drives()` after show so the user sees the window immediately even if the subprocess takes a moment. `MainWindow.run_dependency_check(show_summary)` is the refactored entry point both the launch sequence and the Tools → Check Dependencies menu use. 4 tests cover --version exit code, version string, unknown-flag error, and module importability without side effects.

### Build + smoke test

- [x] T30 — Test harness scaffold (`tests/conftest.py`, fixtures dir)
      Acceptance: `pytest` runs from repo root with no errors (even with no tests yet). conftest exposes any shared fixtures.
      Phase: P0
      Done: `tests/conftest.py` was created in T18 with the session-scoped `qapp` QApplication fixture (offscreen Qt platform set before any Qt import). This task ratifies that scaffold: adds `[tool.pytest.ini_options]` to `pyproject.toml` (testpaths=tests, pythonpath=src so PYTHONPATH no longer needs to be set manually, addopts=-q --strict-markers) and writes `tests/fixtures/README.md` documenting each fixture's provenance (notably that `rip_log_real_whipper_0_7.log` is pulled verbatim from upstream and `rip_log_eac_reference.log` exists only for the format comparison). `python3 -m pytest` from the repo root now works without any extra env vars.

- [x] T31 — python-appimage build harness (`build/build_appimage.sh`, `build/python-appimage/requirements.txt`)
      Acceptance: running `bash build/build_appimage.sh` from repo root produces `platterpus-x86_64.AppImage` at the repo root. Build is reproducible (no `git rev-parse`-time state baked in beyond the package version).
      Phase: P0
      Done: `build/build_appimage.sh` checks prerequisites (python3, `build`, `python-appimage`), builds a wheel from local source via `python -m build`, drops it next to the recipe so pip resolves `platterpus` to the local wheel rather than PyPI, generates a 16×16 placeholder icon if no real one is present (using a hand-rolled PNG generator with no external deps), and invokes `python -m python_appimage build app build/python-appimage/`. Recipe directory has `requirements.txt` (pinned to DEPENDENCIES.md), `entrypoint.sh` (executable script that runs `python -m platterpus` from the bundled interpreter), `platterpus.desktop` (KDE/freedesktop standard), and `README.md`. Build-harness unit tests verify the recipe structure, executable bits, the desktop file shape, the local-wheel self-install pattern, and that the pinned versions match DEPENDENCIES.md.
      **Build verified end-to-end 2026-05-29 (during T32), which surfaced five recipe bugs the unit tests couldn't catch — all now fixed + guarded by new regression tests:**
        1. **`--find-links .` in requirements.txt doesn't work** — python-appimage runs `pip install` once per line from a temp dir, so a standalone option line becomes its own argument-less install. Replaced with `PIP_FIND_LINKS=<recipe dir>` exported by the build script (a pip env var, so it survives pip's `-I` isolated mode).
        2. **`<`/`>` in version pins crash the build** — python-appimage's `system()` does `' '.join(args)` + `shell=True`, so `,<7` is read as a shell redirection ("cannot open 7"). Switched the bounds to the equivalent `~=` operator (`PySide6~=6.7`, `tomli-w~=1.0`).
        3. **`entrypoint` was never bundled** — python-appimage globs `entrypoint.*`, so an extensionless file is ignored and the default AppRun runs the bare interpreter (`--version` printed Python's version). Renamed to `entrypoint.sh`.
        4. **A space in the `.desktop` `Name=` field** ("Platterpus") breaks the unquoted appimagetool command, so the output file is silently never produced. Renamed to `Platterpus`; the build script normalises the artifact to the canonical `platterpus-x86_64.AppImage`.
        5. **No offline/rate-limit path** — python-appimage hits the GitHub API to fetch the CPython base image, which 403s when unauthenticated-rate-limited. Added an optional `PLATTERPUS_BASE_IMAGE` escape hatch to feed a pre-downloaded base image and skip the API. (FUSE-less build hosts also need `APPIMAGE_EXTRACT_AND_RUN=1` for appimagetool.)

- [x] T32 — End-to-end smoke test on Bazzite
      Acceptance: built AppImage launches; dependency check passes (or correctly surfaces missing items through the three tiers); a real audio CD rips end-to-end with AccurateRip results displayed. Resolves the open question in KDD-06 (is libdiscid actually needed on the host?).
      Phase: P0
      Progress (2026-05-29): **Rip pipeline verified end-to-end** on the user's Bazzite + Distrobox + Pioneer BDR-209D with a 16-track CD-R. All tracks ripped, every Test CRC == Copy CRC, "Rip quality 100.00%", "No errors occurred"; FLACs play; `.log`/`.cue`/`.m3u`/`.toc` written; AccurateRip queried and correctly reported "not in DB" (CD-R). **KDD-06 resolved: libdiscid is NOT needed on the host** — whipper (in the container) computes the disc ID and `cd info`/the rip expose it; the GUI never touched libdiscid. **KDD-13 questions answered:** whipper writes a `.cue` (and `.m3u`/`.toc`) next to the FLACs, and captures ISRC/UPC slots (all-zero on this CD-R). Bugs found + fixed this session: CD-R guard (`--cdr`), missing working-dir mkdir, empty track table, frozen pre-track status, blank placeholder rows, default naming template. **AppImage now builds, launches, and self-initialises** (verified 2026-05-29): `bash build/build_appimage.sh` produces `platterpus-x86_64.AppImage`; `--version` prints `platterpus 0.0.1`; a headless (`QT_QPA_PLATFORM=offscreen`) launch brings up the Qt event loop with config created, the MusicBrainz adapter initialised, and the dependency manager probing all four registered deps (host-side whipper/metaflac/flatpak correctly report absent — they live on the host by design; bundled musicbrainzngs reports present). Five build-recipe bugs found + fixed getting there (see build-harness task above). **DONE 2026-05-30: a full 16-track rip completed *through the AppImage* on Bazzite** — `success=True`, every Test CRC == Copy CRC, "Health status: No errors occurred", FLAC/.cue/.m3u/.toc all written to `Unknown Artist/Unknown Album/`. That was the last acceptance criterion; T32 is complete. One AppImage-only bug surfaced and was fixed in the same pass: the bundled (manylinux) CPython ships no CA certificates, so every MusicBrainz HTTPS lookup failed with `CERTIFICATE_VERIFY_FAILED` (disc identification silently broken in the distributed build, even though the editable install worked). Fix: `entrypoint.sh` now points `SSL_CERT_FILE`/`SSL_CERT_DIR` at the host CA bundle (covers Fedora/Bazzite, Debian/Ubuntu, Arch/openSUSE, Alpine layouts); verified the bundled interpreter then completes an HTTPS request to musicbrainz.org. Also from this round of real-use feedback: two-tier progress (overall + current-task bars; the overall bar is monotonic and the pre-track disc scan now animates) and a fidelity summary on the status line ("Done — all N tracks verified, Test/Copy CRCs match") so the user can confirm a secure rip without opening the log.

---

## P1 — backlog (do not start until P0 ships)

P0 shipped 2026-06-01 (v0.1.0), so this backlog is now the active queue; the fence below is kept for the record of how the sections were ordered.

The sub-sections below are ordered by current priority for picking up work:

1. **P1.1 — Install / uninstall ease** is the **highest priority subset** of P1. Items here unblock new contributors at the install step; finish before anything else P1.
2. **P1 — Release milestones** — gating actions for v0.1.0. Merging to main, flipping the repo public, tagging the first release, publishing to PyPI. Most other P1 items remove caveats from the README once these are done.
3. **P1 — EAC bit-perfect parity gaps — ✅ closed in v0.5.8 except INDEX 00.** The old whipper-flag widgets were retired with whipper (KDD-18); the fresh cyanrip overread toggle shipped 2026-07-21 (`-O` — the doc-claimed `-x` never existed), and the gap-handling investigation closed the same day as already-satisfied (cyanrip's default = EAC's, verified upstream). **v0.5.8 closed the remaining four** on the maintainer's "equal-or-stronger rigor, honestly labelled as ours — never forge EAC" principle: an openly-verifiable SHA-256 **log checksum** (KDD-28), a **measured cache-defeat verdict** via `cd-paranoia -A` (KDD-29), **Test & Copy** CRC pairs from `-Z` convergence + a verify-every-track mode (KDD-30), and **read-offset auto-confirmation** by AccurateRip (KDD-31). The one remaining difference is the cue-metadata **`INDEX 00`** question, whose *mechanism is now decided* — build cyanrip from the soft-fork integration branch (KDD-32; `master` already emits it, and it carries PR #115). Not a blocker for the public AppImage.
4. **P1 — UX gaps from real-user testing** — issues surfaced on Bazzite that aren't urgent but make the GUI feel less polished.
5. **P1 — Install automation** — pre-clone host bootstrap script. Blocked on the repo flipping public.
6. **P1 — Documentation backlog** — items that need real-system output from T32 to write authoritatively.

### ⭐ Current plan & priorities (re-ranked 2026-07-21 — START HERE)

The live, ordered work queue — what to pick up next. Difficulty: **S** = a focused session, **M** = 1–2 sessions (may need upstream-source research), **L** = multi-session. **HW** = hardware-gated (needs the user's machine/drive/disc — code-side prep can still be done first). Each entry is deliberately just the queue line; the linked section carries the full context. *(Originally set 2026-06-09; re-ranked 2026-07-21 per the docs-audit consolidation plan, because 11 of the original 15 items were ✅ and the genuinely live workstreams sat in later sections a START-HERE reader never reached. The original numbered list — still cited elsewhere as "current-plan item N" — is preserved with its numbering as ranked history just below.)*

1. **🟡 Trust & supply-chain hardening — open audit follow-ups (M; maintainer-gated in part).** The **verify** half of update authenticity **shipped 2026-07-21** (KDD-26): the `cryptography` dep was approved and is a hard runtime requirement, `update_signing.py` exists, and `update_install.py` is wired fail-closed — dormant until a key exists. **Remaining, maintainer-only:** generate the keypair, bake in the public key, sign the first release (see [docs/architecture.md §6.2](docs/architecture.md)). Separately, full-AppImage byte-reproducibility still needs validating on a real release build. See *P1 — Trust & supply-chain hardening* below.
2. **🟡 cyanrip soft-fork upstream PRs — prepared, env-gated (M).** Both contributions (the `-a`/`-t` colon-parsing fix; full libavcodec encoder args) are researched, patched, and paste-ready in `scripts/cyanrip/` + [docs/cyanrip-fork.md](docs/cyanrip-fork.md); execution (fork → build in the container → issue → PR) needs an environment with cyanrip repo access (local, or a cyanrip-seeded session — this cloud session is scoped to Platterpus only). See the *cyanrip upstream contributions* block below.
3. **⬜ Hardware-gated proof queue — HW (user), S each.** Everything only the Bazzite + BDR-209D rig can prove, consolidated. **The run sheet is [`docs/hardware-test-checklist.md`](docs/hardware-test-checklist.md)** — as of 2026-07-30 it is *consolidated*: it carries **every** outstanding hardware test rather than only the newest release's, grouped by why each is still open, with stable test IDs that are retired once they pass. Work that sheet first; it, not this bullet, is the live list. **First run done 2026-07-26 (partial):** the log checksum verified end-to-end (test 3 ✅, recomputed independently from the real artifact + tamper detected), force-stop/post-cancel recovery held (test 15 ✅), the wizard's `dnf install /usr/bin/cd-paranoia` provides-install + export **succeeded on a real Fedora container** (previously flagged unverified — now proven), and the real `cd-paranoia -A` output was captured and committed as a fixture (the KDD-29 gate is CLOSED). That run also surfaced **five defects, all fixed** (see CHANGELOG `[Unreleased]`): the 90 s probe timeout, the undiagnosable unknown verdict, "Finished with issues." on a successful cache-only run, the EAC log calling offset-variant tracks absent from AccurateRip, and overread rendering "(unknown)". **Second run done 2026-07-26 (v0.5.9, Overread OFF — a complete 14-track rip):** all eight v0.5.9 fixes confirmed on the rig — the cache probe finishes and reaches both the panel and the log as a measured `Yes`, the wizard reports "Done.", the offset trust line reached **"confirmed — two independent sources agree"** (KDD-31 earned on hardware), overread renders `No`, and offset-variant tracks are described correctly — so **tests 2, 5, 14 are ✅**. **⭐ Test 17 is ANSWERED:** the `.cue` carried 14 × `INDEX 01`, no `PREGAP` — the pre-gap gap is real on the deployed cyanrip 0.9.3, so KDD-32's build-cyanrip-from-source step is now **required** and is the run sheet's final part. That run also surfaced **two new honesty defects, both fixed in v0.5.10**: a re-read track's Test & Copy proof never reached the log, and a track whose re-reads *disagreed* rendered as clean. **Third run done 2026-07-26 (v0.5.10, step 1 only):** the Test & Copy rendering fired but paired the convergence proof with the **first pass's** CRC on both swapped tracks (log `52DFDF7D`/`6902BCF0`; files `3D8FCF0C`/`E0036697`) — the swapped-in read's own record now replaces the first pass's (fixed in v0.5.11, regression-pinned). Both problem tracks converged for the first time (`unresolved: false`). **Still open** — the run sheet's own §A–§E are authoritative and the old flat test numbers below were superseded by them on 2026-07-30; everything *not* on the sheet: the `-Z` convergence re-rip (history item 14); the from-scratch wizard/`setup-host.sh` run + drive-setup success screens + README screenshots + Picard UX (history item 10; test-plan Tests 3/5/6); cyanrip WAV parity (proof matrix below); the new test-plan Tests 12–14; a real in-app uninstall run (history item 4); UX gap #3 (timestamp-localized anomalies — needs real anomaly-bearing output); and a live screen-reader (e.g. Orca) session over the announced surfaces (UX gap #4's last fraction, 2026-07-21). *(The EAC gap-handling check was removed from this queue 2026-07-21 — closed as already-satisfied; cyanrip's default matches EAC, verified upstream, no hardware run needed.)*
4. **🟡 Documentation backlog — the 2026-07-21 docs-audit consolidation plan (S–M).** In execution; per-item status under *P1 — Documentation backlog* below.
5. **🟡 UX gap backlog remainder (S–M).** Gap #4 is ✅ complete (the keyboard-reachability sweep + focus-safe live announcements shipped 2026-07-21; only the live screen-reader confirmation rides queue item 3); gap #3 is hardware-gated (queue item 3 above). Canonical ranked table: [docs/ux-design-principles.md](docs/ux-design-principles.md); tracking checklist: history item 15 below.
6. **⛔ CTDB repair (Phase 2) — parked by decision (L; "D → B", maintainer 2026-07-21).** The everyday "beyond EAC" differentiator; its CRC gate cleared 2026-07-07 (KDD-16). **Shipping decided:** *not now* — the documented manual power-user workflow ([docs/manual-ctdb-repair.md](docs/manual-ctdb-repair.md)) covers the rare recovery case (D); wire `ctdb-cli` as an **optional user-installed tool** via the dependency subsystem (Picard model, B) only when a real user actually hits an uncorrectable-error rip CTDB could repair. Bundling a .NET runtime into the AppImage (A) is off the table; a pure-Python parity port (C) stays rejected. So this is no longer "maintainer-gated" — it's demand-gated. See KDD-14 and [docs/eac-parity.md](docs/eac-parity.md) Part B.

8. **[x] ✅ The fork is installed by the app, and "which build" is visible — DONE 2026-08-03 (v0.6.3, KDD-33).** The container switch to the fork was a manual step in a test plan, and it never ran: **every rip through v0.6.2 used the stock COPR `cyanrip 0.9.3`**, including the AccurateRip-verified hardware runs. The maintainer found out by reading the dependency dialog. Fixed at both ends — the setup wizard now builds/installs/**verifies** the pinned fork (`deps/fork_source.py`, `cyanrip_fork` step, additive so a failed build leaves a working ripper), and the dependency check names the build next to the version because the fork keeps upstream's version string on purpose. See KDD-33.

10. **[x] ✅ Two contract-verification gaps closed — DONE 2026-08-03 (v0.6.3).** Both were ours and both were invisible to a green suite. (a) **The input half of the seam was never checked.** We diffed the fork's published log lines against our parser and never their published *flag table* against our argv — and that table had said `-v`/`--version` with no `-V` row for a full round, while all four of our version probes sent `-V`. A rejected version flag exits non-zero, which every probe here reads as "the tool is absent", so installing the fork would have reported the ripper **missing** right after the wizard built it. `tests/test_argv_surface_agreement.py` now does the diff mechanically and fails against round 4's own table with the old flag set. (b) **Our fatal-message fixture inherited the fork's filter.** Their generator ran candidates through a 21-word prefix allowlist; their control-flow re-derivation took the inventory 88 → 104, and our pattern missed all 13 matchable strings it had hidden — two of them ordinary hardware failures reaching the user as a bare "Rip failed." The matcher is now compiled from their published `printf` formats. See `docs/testing.md` §5.ab.

11. **⬜ Round-5 follow-ups the verification surfaced (S–M each, not blocking the round).** Ranked:
   - **HIGH — `Cache defeat:` is captured and discarded.** The fork now prints it; our parser drops it, so the EAC-style log renders `Defeat audio cache : (unknown)` for a fact stated on the line above. A diagnostic-completeness violation in the archival artifact.
   - **HIGH — keep BOTH golden references.** The round-5 log *narrows* coverage vs the round-4 one already committed: no `-Z` secure-read path (so the F1 `Done;`-misattribution class stops being exercised), no over-full-scale `REPLAYGAIN_TRACK_PEAK` > 1.0 (the case the whole sample-peak trap comment exists for), and no custom `-D/-F/-L/-M/-P`. Commit round 5 as a *second* fixture, and ask them to generate future references with `-Z` and a clipping track.
   - **MEDIUM — `Encoder:` and `CD-TEXT:` fall through unrecognised.** `Encoder:` names which libavformat/libavcodec actually encoded the archival FLAC, which is squarely under the say-which-build-produced-an-artifact rule.
   - **MEDIUM — per-track paranoia counters: we asked for W1, they built it, we read none of it.** `TrackResult` has no field. Either graduate it or record the decision.
   - **MEDIUM — `Total time:` / `Duration:` are `MM:SS.FF` in CD frames.** `rip_timing.parse_hms_to_seconds` requires `HH:MM:SS`, so it returns `None` for every fork value and `_enrich_timing_with_disc_duration` is a silent no-op on every fork log. No wrong number is produced; the fact is dropped.
   - **LOW — the status report says "3 track(s) could not be verified as accurate" on a disc where AccurateRip was never queried**, while the per-track rows correctly say "Not checked against the AccurateRip database". The summary is less honest than the rows it summarises.
   - **LOW — `True peak level:` has no field** and falls through silently.
   - **HIGH — the auto-fix addendum invalidates cyanrip's own log checksum, and the naive fix is worse.** We append the supersession block to the ripper's `.log`, after its `Log FUN512:` line; cyanrip has a dedicated `CRIP_LOG_TRAILING_DATA` state, so `cyanrip -Y` reports the file as modified and exits 1 (fork round 5 Q5, measured). But simply moving it to a sidecar **regresses bug #19**: `parse_cyanrip_log` reads `shipped_crcs` *from that appended text* and its own comment calls it "the only statement in the file about which bytes actually shipped", so the EAC-style log would go back to printing the **discarded** first-pass CRC. Attempted and reverted rather than shipped half-done. The real fix is to apply the supersession structurally from the worker's `retried_tracks` (which already reaches the report) *before* rendering, keep the parser's addendum rule for legacy logs, and only then write the sidecar. Needs the whole chain re-verified end to end.
   - **MEDIUM — the album-loudness block is gated on FFmpeg's wording.** `cyanrip_log.py` keys on `^Album Loudness Summary:$`; the fork's stable string is `Album Loudness` (their P2, `cyanrip_encode.c:757`). One FFmpeg rewording empties `album_loudness` entirely — measured. Same class: `I:` / `LRA:` have **no** stable provider source at all, so if we keep them the report must say the source is libavfilter and unpinned rather than silently nulling the key.

9. **⬜ Handshake round 5 — OPEN, and it blocks the v0.6.3 release (S, awaiting the fork).** Sent: `docs/handshake/outbound/round-5.md`. Opened because our argv surface changed (`-c disc/totaldiscs`) and because reading the fork's source at the pin found **two fatal strings absent from its own generated 88-string inventory** (`discnumber %i is larger than totaldiscs %i`, `Cover art already specified for track idx %i!`) — both from calls whose format string sits on a *continuation line*, a systematic blind spot in their generator; a sweep of their `src/` finds exactly those two, so the inventory is 88 → 90. Our surfacing is 90/90. **Waiting on:** their §A–§J return file, then our verification file, then the release. The gate is now enforced where it belongs — `release.yml` runs `scripts/handshake.py --release-gate` before the build (see `docs/testing.md` §5.aa for why the old enforcement was in the wrong place).

7. **[x] ✅ Test-suite Qt teardown — RESOLVED 2026-07-28 (was 🔴).** The suite leaked Qt objects and any cyclic collection could crash the process: measured **5 SIGSEGVs in 5 runs on unmodified `main`**, and 3 in 3 with a detector present. Root cause was three things compounding — `deleteLater()` never executes in a suite with no event loop, post-rip work runs on daemon threads, and a cyclic collection can begin on *any* thread, so whichever thread was inside the collector when the GUI thread destroyed a widget was the one that died (hence tracebacks in unrelated files). **Fixed** by pausing the cyclic collector for the duration of each test and collecting at one deterministic point on the main thread *after* every worker is joined; `stop_window_threads` now covers all seven QThread slots and all nine daemon slots; a new `threading.Thread` backstop mirrors the QThread one; and one test that undid its monkeypatches while its worker still ran (leaking a 120-second `compute_digests`) was corrected. **Verified at the root:** `tests/test_qt_teardown_fitness.py` forces a full collection every run and asserts no worker survived — **0 crashes in 10 randomized runs and 0 in 8 under `--cov`**. Full write-up, measurement table, and the two plausible-but-worse fixes that were tried and rejected: `docs/testing.md` §5.w.

### 2026-06-09 plan — ranked history (numbering preserved; cited elsewhere as "current-plan item N")

The queue as set 2026-06-09 and worked down through 2026-07 — 11 of its 15 items shipped. Kept with its original numbering as the historical record (same pattern as the 2026-05-30 "Ranked execution order" further down) because other text cites "current-plan item N"; the still-open fractions of items 10/14/15 are ranked in the live queue above.

1. **✅ cyanrip stdout progress parsing — DONE 2026-06-09.** `RipWorker` now parses cyanrip's `\r`-redrawn lines (`Ripping[ and encoding] track N, progress - X%[, ETA - …]`, `Track N ripped and encoded successfully|with errors`, total from the start report's `Disc tracks:`) into the same banded overall/task progress, current-track highlight, and live status (with ETA) as whipper. **No plumbing change needed:** `Popen(text=True)` universal-newlines translates bare `\r` to `\n`, so each redraw already reaches `log_lines()` as its own line (verified empirically). Formats verified against cyanrip master `cyanrip_main.c`.
2. **✅ cyanrip log fidelity verdict — DONE 2026-06-09.** `parsers/cyanrip_log.py` (formats verified against `cyanrip_log.c`) parses the per-track EAC CRC32 (→ `copy_crc`; `test_crc` stays empty — cyanrip has no dual read), AccurateRip v1/v2 + confidence, preemphasis, drive/offset, and the finish report ("Ripping errors: 0" normalized to whipper's "No errors occurred") into the shared `RipLog`. `_on_rip_finished` sniffs the log format (`looks_like_cyanrip_log`) rather than trusting the configured backend; `_fidelity_summary` words the cyanrip verdict around its actual checks ("ripped cleanly, no read errors" + "AccurateRip: N/M") — never claims a Test/Copy pass that didn't run. Property test added. *Golden fixture from a real hardware log still wanted (test-plan Test 8 step 6).*
3. **✅ Hardware parity run — resolved 2026-06-27/30.** The cyanrip half ran on real hardware 2026-06-27 (the Police disc, 12/14 byte-identical vs EAC; T3/T5 divergences documented in `output_reference/cyanrip_flac/`), which settled KDD-18 — whipper was then removed entirely 2026-06-30 (KDD-18 amendment), so the "both backends" comparison is no longer possible or needed. Remaining genuinely-open piece: a from-scratch wizard-install run on clean hardware (tracked in item 10).
4. **✅ In-app Uninstaller — DONE 2026-06-09 (standing user request, 2026-06-08).** `deps/host_teardown.py` (`HostTeardown`) is the reverse arm of the bootstrap: idempotent steps (shortcuts → exports → container → whipper.conf → AppImage → app settings/logs LAST, so the log survives a failed step), injectable runner + removers, dry-run, per-step report; **never targets distrobox/podman or music** (test-pinned: the only mutating command is `distrobox rm --force ripping`). `ui/uninstall_dialog.py` (Tools → Uninstall Platterpus…, separated at the menu bottom) double-gates with a confirm prompt + per-piece checkboxes (container / whipper.conf; AppImage step only when running as one), reuses `HostSetupWorker` (now typed against a `StepEngine` Protocol); on success the main window offers to close (settings no longer exist on disk). `uninstall.sh` gained the cyanrip-export parity fix in the same change. *Hardware-gated final proof: a real uninstall run on the Bazzite box.*
5. **✅ App + Uninstaller desktop icons & Multimedia menu category — DONE 2026-06-09.** Verified: every `.desktop` we write (AppImage self-integration, the bundled recipe, dev-setup.sh) already carries `Categories=AudioVideo;Audio;` — AudioVideo IS the Multimedia menu (freedesktop spec); nothing to fix, real-menu confirmation rides along with the next hardware session. Added: `integrate()` now also writes an **"Uninstall Platterpus"** menu entry (`platterpus-uninstall.desktop`, `Categories=System;`, menu-only — deliberately not on the Desktop) that launches the new **`platterpus --uninstall`** mode (app.py opens just the UninstallDialog, no adapters/main window). The teardown engine already removes that entry.
6. **✅ AppImage self-update (zsync) — DONE 2026-06-09 (KDD-17b, the last zero-CLI slice).** `build_appimage.sh` re-packs the finished AppImage with appimagetool `-u "gh-releases-zsync|rmccann-hub|…|platterpus-x86_64.AppImage.zsync"` (python-appimage can't pass `-u` itself; the script reuses its cached appimagetool) and emits the `.zsync` when `zsyncmake` is present; `release.yml` installs zsync and uploads the `.zsync`, and the `.sha256` is generated AFTER the embed so it covers the shipped file. In-app: **Help → Check for updates…** (`update_check.py` + `UpdateCheckWorker`, releases-list API — not `/latest`, which hides v0.* pre-releases) reports up-to-date / hands off to `appimageupdatetool` when installed / opens the release page — never downloads payloads itself (KDD-17). *Hardware/release-gated proof: embed + `.zsync` are verifiable on the v0.2.0 release artifact; the first real delta update can only be exercised when the NEXT release exists (v0.2.0 → v0.3.0).*
7. **✅ setup-host.sh `--cyanrip` parity — DONE 2026-06-09.** New `--cyanrip` flag: writes the same COPR stanza the wizard writes (positional-`"$1"` so `$releasever` stays literal; GPG-checked; container-only), `dnf install -y cyanrip`, exports `/usr/bin/cyanrip`. Smoke tests pin the stanza's version-genericity + gpgcheck. **Keep the script and `deps/host_setup.py` stanzas in sync.**
8. **✅ CTDB verify — COMPLETE (GUI wiring 2026-06-17; CRC hardware-validated 2026-07-07, v0.4.20). This item is the canonical status home for CTDB verify.** GUI wiring (Test 1b): the verify runs off the GUI thread after a rip (joining the post-rip metaflac thread first so it never decodes a file mid-rewrite), gated by `Config.ctdb_verify_after_rip` (default on); the verdict renders under the AccurateRip table. **`toc=` wire format RESOLVED (0.4.5, verified against the live server — KDD-14).** **CRC hardware-validated (KDD-16):** a `--ctdb-calibrate` run on the real Police-disc rip reproduced a stored CTDB CRC at aligned offset 0; `crc.CRC_VALIDATED` flipped to `True` with the vector pinned as a regression fixture (`crc.CONFIRMED_VECTOR`) — a match now reads **verified**, and v0.4.23 removed the stale "experimental" caveats from the UI copy. The wizard has exported host `flac` for the decoder since v0.3.5. CTDB **repair** (L, .NET bundling question) stays parked — see the feasibility doc.
9. **✅ Backend-independent cover art — M (elevated and SHIPPED 2026-06-13; the user's stated goal: "good music, good cover image, good everything").** As built: `adapters/cover_art.py` (CAA `/front` fetch, stdlib urllib, injectable fetcher, magic-byte image sniffing, never raises) + `MetaflacAdapter.embed_picture` (PICTURE block replace, no duplicates) + a post-rip daemon thread in MainWindow gated by `cover_art.plan_actions`. Outcome line lands in the rip log view. Hardware proof rides the next hardware session: a cyanrip rip of an identified disc should produce FLACs with embedded front covers. *Original problem statement (pre-fix, kept for the record — whipper was still a backend then):* cover art was whipper-only, because the cyanrip metadata model (-N + GUI-fed tags) deliberately skips cyanrip's own MB/CAA lookup, which is where its art came from. Fix at the right altitude: the GUI fetches the front cover itself from the **Cover Art Archive** (`coverartarchive.org/release/<MBID>/front`) using the release ID it already has — host-side, off-thread, cached per release — and embeds it in the ripped FLACs via the existing metaflac adapter (`--import-picture-from`), optionally also saving `cover.jpg` in the album folder. Works identically for BOTH backends; un-greys the cover-art Settings row under cyanrip; honors Critical Rule #5 (we query, never the ripper). Degrades silently when CAA has no art.
10. **⬜ Remaining hardware-gated doc items — HW (user), S each.** Real-run confirmations: `setup-host.sh` / host wizard from scratch, the drive-setup wizard's "what success looks like" screens (the whipper-era `drive analyze`/`offset find` strings are gone — test-plan Tests 3–4 need re-scoping, see the Documentation backlog), README screenshots (Test 5), Picard UX (Test 6). *(PyPI Trusted-Publisher setup — Test 7 — is **DONE**: the package publishes automatically on every tagged release.)*
11. **✅ MainWindow decomposition (KDD-19) — COMPLETE 2026-06-13 (user-requested "full refactor").** The 1707-line god-object was split into six cohesive **mixins** `MainWindow` inherits (so `window._x` test access + Qt signal wiring keep working): `main_window_helpers.py` (pure fns) + `UpdateMixin` / `RipMixin` / `ProvisioningMixin` / `DriveMixin` / `DependencyMixin`. `main_window.py` is now a ~460-line assembler (construction, menus, signal wiring, MusicBrainz slots, Settings). Every extraction was test-guarded (777 green, one concern per commit). **Lesson banked (docs/architecture.md §5, testing.md #8):** moving code between modules means moving its monkeypatch targets too. **Still open (separate from the MainWindow split):** assess the other large files (`whipper_backend`, `host_setup`, `rip_worker`, `settings_dialog`) for real seams, and a naming/comment/type-hint/import consistency sweep — see item 13.
12. **✅ GUI-thread responsiveness sweep — DONE 2026-06-14 (started 2026-06-13).** The bug class behind the in-app-update freeze is *synchronous blocking calls on the Qt GUI thread*. Handled: `appimage_integration._default_refresh` (kbuildsycoca) and `_mark_trusted` (gio) → fire-and-forget `Popen`; **(a) launch dependency check now runs OFF the GUI thread — DONE 2026-06-14:** `run_dependency_check_async()` + `DependencyCheckWorker` probe on a worker thread, the report is applied on the GUI thread (where resolver dialogs live); `app.py` uses it at launch so a cold-container `whipper --version` can't freeze the just-shown window. The **lint/grep guard is also done** — `tests/test_gui_thread_discipline.py` (AST fitness test) fails the build on any `subprocess.run`/`urlopen`/`time.sleep` in `ui/`. **(b) `disc_info` now runs OFF the GUI thread too — DONE 2026-06-14:** `workers/disc_info_worker.py::DiscInfoWorker` probes the disc on a QThread per drive change; `_on_drive_changed` is split into the trigger (`_start_disc_info`) + `_on_disc_info_ready`/`_on_disc_info_failed` handlers — so selecting a drive (or the launch auto-select) never freezes the window. **(c) launch `list_drives` now runs OFF the GUI thread too — DONE 2026-06-14:** `workers/drive_list_worker.py::DriveListWorker` runs `list_drives` (whipper `drive list`, container entry) on a QThread; `refresh_drives` (launch + post-host-setup) populates the picker on the GUI thread via the new `DrivePicker.populate()`/`show_error()` split. The picker's own **Refresh button stays synchronous** (user-initiated). **Net: the entire launch path is now non-blocking** — all three container-entering probes (deps, drive list, disc info) are off-thread. **(d) post-rip metaflac tagging now runs OFF the GUI thread too — ✅ DONE 2026-06-17:** `_on_rip_finished` used to call `run_unknown_post_processing` synchronously, so a 16-track album froze the window for ~15-30s (a subprocess per file) right when the rip finished. Tagging and the post-rip cover-art embed both shell out to metaflac on the *same* FLAC files, so they now run **sequentially on ONE post-rip daemon thread** (`_start_post_rip_processing`: tag first, then cover art) — never concurrently, which would race two metaflac processes on one file → corrupted/lost tags or artwork. `run_unknown_post_processing` stays the synchronous worker body (tests call it directly); it's just invoked off-thread now. Behavioural regression test added (`test_unknown_rip_tagging_runs_off_the_gui_thread`: blocks metaflac on an Event, asserts the finish handler returns before tagging completes) — the AST fitness guard can't catch this one because the blocking subprocess is reached *indirectly* through the adapter. **This was the last remaining synchronous blocking call in the app — the responsiveness sweep is fully complete.**
13. **✅ Codebase consistency sweep + large-file seam assessment — DONE 2026-06-13 (full code/doc audit).** (a) **Large files assessed → all single-responsibility, left intact** (cohesion over line count): `adapters/whipper_backend.py` (the whipper adapter: ABC + impl + handle + helpers), `deps/host_setup.py` (one idempotent bootstrap engine), `workers/rip_worker.py` (one cancellable off-thread rip + progress parsing), `ui/settings_dialog.py` (one Config-editing dialog). No real seams; splitting would hurt readability. (b) **Consistency pass:** fixed the type-hint gaps the audit found (`_default_open → http.client.HTTPResponse`, `_build_host_setup → HostSetup` via `TYPE_CHECKING`, `_show_dep_summary`'s `optional_missing → list[MissingItem] | None`, `_on_update_install_finished`'s `dialog → QProgressDialog`); fixed a CI-red `ruff format` lapse in `tests/test_ui_main_window.py`. Audit found **zero correctness bugs, zero dead code, no blocking-on-GUI-thread regressions.**

14. **🟡 EAC-parity follow-up (audio-trust focus) — code SHIPPED 2026-06-28; convergence HW-gated.** Continuing the EAC-parity brief ([docs/eac-parity.md](docs/eac-parity.md), [docs/eac-parity.md](docs/eac-parity.md)). **(a) ✅ cyanrip `-Z N` "re-rip until reads match"** — `Config.secure_rerip_matches` (0=off) → `RipParameters` → backend ABC → cyanrip argv; whipper ignores it; Settings spin box greyed for whipper. The lighter, no-new-dep answer to a Track-3-class near-miss. *HW-gated:* convergence effect needs a real marginal-disc run on the BDR-209D (re-rip with it on, re-run `scripts/eac_parity.py` vs the EAC baseline). **(b) ✅ Verification verdict banner** — colour-coded at-a-glance trust headline above the results table, plus one shared `confidence ≥ 1` rule (`parsers/rip_log.track_accuraterip_verified`) across the banner, disc panel, status line, and EAC renderer (fixed a real bug: the disc panel string-matched "exact match" and under-counted cyanrip rips). **(c) ✅ Parity made routine** — `tests/test_parity.py` pins the committed cyanrip-vs-EAC result (12/14, T3+T5) as a no-hardware regression guard. **(d) ✅ Honest EAC-layout log renderer** — `eac_log_export.py` + `scripts/render_eac_log.py` render our rip into EAC's layout, clearly attributed and **never signed** (an EAC-signed log = provenance forgery; not pursued). **Decisions for the maintainer (in the feasibility doc):** tracker-accepted EAC logs (recommend no — forgery), in-app CTDB repair (defer — heavy .NET/Mono dep + blocked on CRC hardware-validation).

15. **🟡 UX trust-first improvements (from the EAC-UX deep-research, 2026-06-28).** The ranked gap table — each gap's rationale, size, and shipped detail — lives **canonically in [docs/ux-design-principles.md](docs/ux-design-principles.md)** (code comments cite its gap numbering; this entry drifted from it once, which is why it is now only the tracking checklist):
    - [x] Gap 1 — Goal presets (shipped 2026-06-28, 0.4.0)
    - [x] Gap 2 — Machine-readable `.platterpus.json` log (shipped 2026-06-28)
    - [ ] Gap 3 — Timestamp-localized anomalies + one-click playback (hardware-gated)
    - [x] Gap 4 — Accessibility (names pass 0.4.4; keyboard-reachability sweep + focus-safe live announcements DONE 2026-07-21; a live screen-reader session on the rig is the one hardware-gated confirmation still owed — queued in live item 3)
    - [x] Gap 5 — Outcome-oriented wording (shipped 2026-06-29)
    - [x] Gap 6 — Drive profiles keyed by stable fingerprint (record/display/guard ledger shipped 2026-06-29; per-drive offset *application* deferred as hardware-gated — KDD-23)

*Parked / later (unchanged ranking):* multi-disc queue, multi-drive, udev auto-detect, ReplayGain, library auto-move (all P1 backlog); EAC-style signed log checksum (LOW — and now documented as provenance forgery, not merely hard); single-file disc image + INDEX 00 pre-gaps (maintainer/HW-gated, see the investigation doc); upstream whipper bug-fix PRs (opportunistic). *(WavPack/MP3/WAV encoders SHIPPED 2026-06-26 — see the encoder-outputs item below.)*

**Ranked execution order (set 2026-05-30, after the "EAC successor" research review; updated 2026-06-02 after v0.1.0 shipped):**
1. **✅ Release milestones** (merge → public → tag `v0.1.0` → publish AppImage) — **done 2026-06-01.** v0.1.0 is live with the AppImage + installers attached. *(PyPI wheel publish: workflow shipped 2026-06-02; Trusted Publisher configured — the package publishes automatically on every tagged release.)*
2. **✅ Drive setup wizard** (write-enabled; PLANNING.md KDD-15) — done 2026-05-30; see P1.1.
3. **✅ Drive-access permission diagnostics** — done 2026-05-30; see P1.1.
4. **✅ EAC parity-gap Settings widgets** (cover art / force-overread / max-retries / keep-going) — done 2026-05-30; below.
5. **✅ CTDB verify (read-only)** — Phase 1 of KDD-14. Library landed 2026-06-03 (clean-room per KDD-16); GUI-wired 2026-06-17; `toc=` wire format verified live 0.4.5; **CRC hardware-validated 2026-07-07 (v0.4.20)**. Status is canonical in **current-plan item 8** — this row is the historical rank record.
6. **⬜ CTDB repair (parity, wrap `ctdb-cli`, explicit trigger)** — Phase 2 of KDD-14; the headline EAC++ differentiator. Note: `ctdb-cli` is .NET 10 (not C), so AppImage bundling is heavy — bundle-vs-optional-install is undecided.
7. **🟡 ⭐ HIGH PRIORITY — Zero-CLI distribution (PLANNING.md [KDD-17](PLANNING.md), user-approved 2026-06-04).** Goal: a non-technical user touches no terminal — download one file, double-click, done. Three independently-shippable pieces: (a) **[x] self-integrate on first run — SHIPPED 2026-06-05:** `appimage_integration.py` offers (first AppImage run, one-time) to write its own `.desktop` + icon and set the AppImage +x, so it becomes a menu app; supersedes `install-appimage.sh`; no-op on source/pipx. (b) **self-update** via AppImage update-information (zsync) + `.sha256` verify — *not built yet*; (c) **[x] GUI first-run host wizard — SHIPPED 2026-06-05:** `deps/host_setup.py` (idempotent bootstrap engine, injectable runner, dry-run, fully unit-tested) + `ui/host_setup_dialog.py` + `workers/host_setup_worker.py`, offered on first launch when whipper is absent and on **Tools → Set up Platterpus…**. Installs Distrobox + container backend + the `ripping` container + whipper + host export; host-root installs use **`pkexec`** (graphical polkit, no TTY) and are skipped entirely on Bazzite/Silverblue. *Final proof outstanding:* a real from-scratch run on hardware (the command execution is the hardware-gated part; orchestration is unit-tested + dry-run-validated). Rejected: Flatpak (Critical Rule #3) and a bespoke download stub. See KDD-17 + P1.1 below.
8. **✅ Auto drive-offset lookup (backend-independent; high-value). DONE 2026-06-05.** Surfaced by real-hardware testing: whipper's `offset find` is "primitive" and failed on a Pioneer BDR-209D even with a recognizable CD. Shipped ([docs/archive/offset-investigation-2026-06.md](docs/archive/offset-investigation-2026-06.md)): `adapters/accuraterip_offsets.py` resolves the offset by drive vendor+model and the wizard pre-fills it for one-click save (no disc, no whipper probe). The **full AccurateRip `DriveOffsets.bin` list (~4,800 drives) is imported and bundled** in-code (`accuraterip_offsets_data.py`); the 69-byte record format was reverse-engineered and **validated against the known BDR-209D=+667** (importer `scripts/update_drive_offsets.py` refuses to write unless that sentinel passes). Works offline for any drive; layered user-CSV > curated > bundled. *Final proof outstanding:* a real from-scratch wizard run on hardware.
9. **🟡 `CyanripImpl` successor backend (PLANNING.md [KDD-18](PLANNING.md), decided 2026-06-04).** whipper is stalled (last release 2021-05) and its cd-paranoia has a real **>587 read-offset bug** that fails tracks on the BDR-209D (+667) — confirmed on hardware. **cyanrip** (active, C/FFmpeg, LGPL-2.1, AccurateRip v1/v2 + EAC CRC, applies the offset via `-s` with its own paranoia → no >587 bug) is the successor. **Phase 1 SHIPPED 2026-06-08:** `adapters/cyanrip_backend.py` (`CyanripImpl`) behind the ABC, `Config.ripper_backend` selector wired in app.py (default whipper). Tested core = rip argv builder, `version`, `find_offset`, backend-independent drive scan. **Phase 2 (2026-06-09): Settings UI toggle** (whipper | cyanrip) shipped. **Phase 3 (2026-06-09): container packaging/provisioning SHIPPED** — research resolved (Fedora + RPM Fusion do NOT package cyanrip; the COPR `barsnick/non-fed` has 0.9.3.1 built for F42–44, GPG-checked — see the audit doc's "Packaging research" section): the host-setup wizard now has an optional cyanrip step (`HostSetup.include_cyanrip`, on when `Config.ripper_backend == "cyanrip"`) that writes the COPR `.repo` stanza in-container, `dnf install`s cyanrip, and `distrobox-export`s it to `~/.local/bin/cyanrip`; switching the Settings backend to cyanrip offers the wizard if cyanrip is missing; app.py prefers the exported absolute path. *Follow-ups:* `setup-host.sh` CLI parity (a `--cyanrip` flag) and `uninstall.sh` removal of `~/.local/bin/cyanrip` (fold into the in-app Uninstaller work). **Phase 4 (2026-06-09): `disc_info` SHIPPED** — `CyanripImpl.disc_info` runs `-I -N` (offline; DiscID/CDDB computed locally from the TOC per cyanrip's discid.c) and `parsers/cyanrip_info.py` parses the report into the shared `DiscInfo` (exact labels verified against cyanrip master's `cyanrip_log_start_report`; property-based never-raises test included). **Phase 5 (2026-06-09): metadata model + template mapping + unified Settings SHIPPED** — rips snapshot the track table into `RipMetadata` (new ABC param; whipper ignores it); cyanrip always runs `-N` and is fed `-a`/`-t` (values escaped for `av_dict_parse_string`; release MBID recorded as a tag) so known-disc rips need no in-container network and can't pick the wrong release; whipper `%`-templates translate to cyanrip `-D`/`-F` `{…}` schemes (`scheme_from_template`) for the same library layout; Settings is one unified page — whipper-only options (CD-R, cover art, overread, keep-going, whipper path) grey out under cyanrip with a why+how-to-re-enable tooltip, values preserved. **Remaining:** cyanrip stdout progress parsing (bars sit still during a cyanrip rip; completion/result still correct), cyanrip log parsing for the fidelity verdict, and the hardware parity run. See [docs/archive/ecosystem-audit-2026-06.md](docs/archive/ecosystem-audit-2026-06.md). **Never fork whipper.** CTDB is backend-independent and unaffected.

*Downgraded:* Test & Copy dual-pass — whipper already emits a per-track Test CRC and Copy CRC, so the guarantee is already delivered (see P2).

High-level feature backlog (not bucketed into a sub-section because each is small):

- **[x] Eject button + auto-eject toggle. Done 2026-06-02.** Manual **Eject** button on the `DrivePicker` (emits `eject_requested(device)`; MainWindow ejects off a daemon thread via the existing `drive_control.eject_drive`, mirroring the force-stop pattern). New `Config.auto_eject_after_rip` (default off) + Settings checkbox; on a *successful* rip `_on_rip_finished` auto-ejects the just-ripped drive (skipped on failure/cancel so the disc stays in for a retry). User guide updated. Tests in `test_ui_drive_picker`, `test_ui_settings_dialog`, `test_config`, `test_ui_main_window`.
- **[ ]** Re-evaluate a vetted cyanrip `-f` offset-detect in the drive-setup wizard (maintainer call). The 2026-07-21 flag verification confirmed `-f` IS a real "find drive offset" mode (needs an AccurateRip-listed disc in the drive) — the 2026-06 removal was about our mis-scraped integration (read a default 0, silently overrode the list value), not the capability. A redo needs trustworthy output parsing + agreement-with-the-list confidence rules (KDD-23 style), and hardware validation.
- **[ ]** Multi-disc queue
- **[x]** Live progress bars per track — **DONE 2026-07-21:** the track table's Status column now paints a real progress bar (with the percent as its text) on the currently-ripping row, fed by the same worker task-percent stream as the bottom bar (`TrackStatusDelegate` + `PROGRESS_ROLE`; DisplayRole stays textual for assistive tech). Finished rows drop the bar for "✓ Done" — never a stale frozen bar.
- **[ ]** Multi-drive support
- **[x]** ~~udev-driven auto-detect on disc insert~~ — **closed as satisfied 2026-07-21 (audited):** the outcome (a freshly-inserted disc is picked up with no manual Rescan) has been delivered since 0.4.x by `drive_media.MediaWatcher` — a 2.5s `CDROM_DRIVE_STATUS` poll (never spins the disc) + a transition-detecting state machine that auto-rescans while idle. A udev/DBus listener would only shave the ≤2.5s poll latency at the cost of a new integration surface; not worth it unless a real case surfaces that polling misses. (Live-hardware confirmation of the watcher itself is already tracked in the test plan.)
- **[x]** ~~ReplayGain calculation~~ — **closed as satisfied 2026-07-21 (audited against upstream master):** cyanrip computes EBU R128 loudness on every rip and writes the full tag set by default (`REPLAYGAIN_TRACK_GAIN/RANGE/PEAK`, `REPLAYGAIN_ALBUM_GAIN/RANGE/PEAK`, `R128_TRACK_GAIN`, `R128_ALBUM_GAIN`, reference loudness — gated only by `-K`, which Platterpus never passes), and the results-pane/JSON already surface album loudness. Derived MP3/WavPack copies carry the tags via the transcode's `-map_metadata 0` (WAV can't hold tags — already warned in Settings); that carriage is worth an eyeball on the next hardware session, but nothing needs building.
- **[x]** Auto-move completed rips to a library folder — **DONE 2026-07-21:** Settings → "Move finished rips to" (`Config.library_dir`, empty = off). The album folder moves only after **every** post-rip worker settles (tag/cover/transcode, the verification suite, checksums, the comparison scan, the debounced report write) — a 500ms settlement poll gates it, the rip generation abandons a superseded move, and the actual move runs on the shared generation-guarded daemon (`library_move.move_album_folder`: never overwrites — collisions get a "(N)" sibling; refuses self-nesting/workspace-root moves). The post-rip buttons repoint to the new home; the re-rip comparison now also scans the library (`find_prior_report` extra_roots).
- **[x] Additional encoding outputs: WavPack, MP3, and WAV — SHIPPED 2026-06-26** (maintainer sign-off; flipped Critical Rule #4 to "FLAC is the default/master, others derived"). **Design → [docs/archive/mp3-wav-support-2026-06.md](docs/archive/mp3-wav-support-2026-06.md) (archived 2026-08-06).** Built: `adapters/transcode.py` now does FLAC→**WavPack** (`-c:a wavpack`, lossless, APEv2 tags) in addition to MP3 (`-q:a 0` VBR + ID3/APIC cover) and WAV (`pcm_s16le`); the **Settings → Output format** selector (FLAC/WavPack/MP3/WAV) + a live WAV no-tags/art warning; the transcode folded into the post-rip daemon thread (after tag→cover→re-compress, reading the final FLACs) via a `transcode_done` signal; `to_config()` now round-trips `output_format` (+ preserves `mp3_vbr_quality`, which had been silently reset). **Transcode-always model** (§4(b)): both backends rip FLAC, then derive — so MP3 is best-practice VBR on *both* (cyanrip's native MP3 is only CBR) and the FLAC master always exists. `ffmpeg` is the single encoder dep (already registered in the subsystem — no bespoke install code, Critical Rule #6). +11 tests. **Known limitation:** embedding cover art *inside* `.wv` needs the standalone `wavpack` tool (ffmpeg's muxer is audio-only) — deferred; the folder `cover.<ext>` is the universal image. **Backend rip parity proofs (P2 below) stay open** — those await real-hardware rips, not code.
  - **Verified findings (2026-06-23, replacing the earlier "verify-before-relying" bank):**
    - **whipper is FLAC-only** (profiles removed in v0.5.0) → MP3/WAV for the whipper path is a **post-rip re-encode**, not native. **cyanrip is natively multi-format** via `-o` (incl. `wav`, `mp3`; lossy bitrate `-b`, default 256).
    - **MP3/LAME `noise_shaping_amp` bug (#516)** is real + still open (LAME 3.100.1 is the last release) **but CBR/ABR-only — NOT VBR.** Use **VBR `-V0`**, joint-stereo ON; the `-q 4` workaround only matters if we ever ship CBR. Via FFmpeg/libmp3lame (cyanrip + a whipper re-encode) `-q:a 0` = `-V0`; the standalone-`-q` bug is a different code path → non-issue for VBR.
    - **WAV:** no RF64 needed at CD scope (~800 MB ≪ 4 GiB); **WAV carries no rich tags or cover art** (RIFF INFO only) → must warn the user (collides with the "good everything" north star). MP3 is *transparent*, not archival — keep FLAC the master.
  - See the design doc for the routing (Config `output_format`, a `native_output_formats()` capability flag, a post-rip `transcode.py` adapter modelled on `flac_recompress.py`, and `ffmpeg` as the single transcode dep).

### ⭐ EAC output-parity proof matrix (`output_reference/`)

Prove each backend reproduces EAC bit-for-bit, and **commit the proof**. The EAC
baseline (log + cue, *The Police — …: The Classics*, BDR-209D, offset +667) is
banked at `output_reference/EAC_flac/`, and the checker is built:
`scripts/eac_parity.py` (logic in `platterpus.parity`) diffs per-track `Copy CRC`
across EAC/whipper/cyanrip logs and exits non-zero unless every track matches.

**Each task = HW (user):** rip the baseline disc with cyanrip (the sole backend since 2026-06-30 — KDD-18) in that format,
run `python3 scripts/eac_parity.py output_reference/EAC_flac/eac_baseline_police_classics.log <the rip's .log>`,
and when it passes, commit the backend's `.log` (+ `.cue`) into the matching
`output_reference/` dir as the durable proof. **Do NOT commit audio** (public
repo + copyright; the CRCs are the proof). Ordered by format priority:

*Priority 1 — FLAC (v1 archival format):*
- **[~]** ~~whipper FLAC parity~~ — **retired: whipper removed 2026-06-30 (KDD-18)**; row kept as the record (the >587-offset question was settled by the cyanrip run below)
- **[~]** cyanrip FLAC parity → `output_reference/cyanrip_flac/` — **proof committed 2026-06-27: 12/14 byte-identical vs EAC** (T3 divergence + T5 disc spot — documented near-parity; pinned by `tests/test_parity.py`)

*Priority 2 — WAV (lossless → same Copy CRCs as FLAC):*
- **[~]** EAC "WAV" reference stored → `output_reference/EAC_wav/` (2026-06-25, **13/14** vs the FLAC baseline — track 3 read error this session; best run so far). ⚠️ **It's actually WavPack** (`wavpack -h -m`), not plain PCM WAV — equivalent for extraction parity (lossless) but a different format/encoder; see its README. Re-rip with a plain-WAV encoder to replace if a true WAV reference is wanted.
- **[~]** ~~whipper WAV parity~~ — **retired: whipper removed 2026-06-30 (KDD-18)**
- **[ ]** cyanrip WAV parity → `output_reference/cyanrip_wav/`

*Priority 3 — MP3 (P1; lossy → "parity" = same extraction CRCs + correct encoder/tags, not bit-identical audio):*
- **[~]** EAC MP3 reference stored → `output_reference/EAC_mp3/` (2026-06-25, **imperfect**: 12/14 vs the FLAC baseline — tracks 3/4 read errors this session; kept for the encoder-config reference `lame -V 0` + ID3. Re-rip clean to replace; see its README).
- **[~]** ~~whipper MP3 parity~~ — **retired: whipper removed 2026-06-30 (KDD-18)**
- **[~]** cyanrip MP3 parity → `output_reference/cyanrip_mp3/` — **proof committed 2026-06-27: 13/14 extraction parity vs EAC**

Done so far: **[x]** EAC baseline committed; **[x]** parity checker + tests
(`scripts/eac_parity.py`, `parsers/eac_log.py`, `platterpus.parity`); **[x]**
WAV/MP3 parity *semantics* pinned (WAV reuses the FLAC baseline; MP3 = extraction
CRC only) — `tests/test_parity.py`, [docs/archive/mp3-wav-support-2026-06.md](docs/archive/mp3-wav-support-2026-06.md) §1;
**[x]** checker reads EAC's native UTF-16 logs (was UTF-8-only → false 0/N).
So the one open row (cyanrip WAV) only awaits a real rip — the checker is ready.

### P1 — EAC bit-perfect parity gaps

The following whipper CLI options exist but aren't currently surfaced in our Settings dialog. Each is a small addition: a Config field, a Settings widget, a `RipParameters` field, and a flag in `WhipperHostExportedImpl.rip()`. The reference for what "should" be exposed is the EAC bit-perfect guide audit in [PLANNING.md KDD-13](PLANNING.md).

- **[x] Cover art (embed + save).** Done 2026-05-30. Whipper's `-C/--cover-art` — **actual choices are `file|embed|complete`** (the earlier `none/embedded/file` guess was wrong; confirmed against `whipper/command/cd.py`). Settings dropdown maps "Don't fetch"→`""` (flag omitted), "Embed in FLAC"→`embed`, "Save as file"→`file`, "Embed and save file"→`complete`. **Behavior change:** `Config.cover_art` defaults to `embed` for EAC parity, so a rip now fetches art over the network by default (best-effort; an unidentified disc just gets none). `RipParameters.cover_art`; flag passthrough.
- **[x] Force overread into lead-in/lead-out — REBUILT cyanrip-native, DONE 2026-07-21.** The whipper-era `-x/--force-overread` plumbing was removed with whipper (KDD-18); the fresh task shipped as the Settings "Overread" toggle → `Config.force_overread` → `RipParameters` → cyanrip **`-O`**, off by default (EAC's baseline setting, and how the 12/14 parity proof matched). **Flag-letter correction (same day):** this row and `docs/dependency-contracts.md` previously claimed cyanrip has "its own `-x` flag" — **`-x` does not exist in cyanrip's getopt at all** (verified against the deployed 0.9.3.1 *and* master); wiring the documented letter would have aborted every overread rip. The whipper flag really was `-x`, which is likely the mix-up's origin. Upstream's own caveat ("may freeze if unsupported by drive") is surfaced in the tooltip; effect confirmed only by a future hardware run (like every rip flag).
- **[x] Max retries.** Done 2026-05-30. `-r/--max-retries N`, default 5 (whipper's own). `Config.max_retries` + Settings spinbox (0–100) + `RipParameters.max_retries`; always passed (no-op at 5). Still current: cyanrip has its own `-r` and this Settings widget is live.
- **[~] Keep going on track failure — superseded, cyanrip-native.** Was done 2026-05-30 as whipper's `-k/--keep-going` (`Config.keep_going` + Settings toggle + `RipParameters.keep_going` + flag); removed with whipper (KDD-18). cyanrip needs no equivalent flag — its rip loop is cyanrip-native and there is no Settings toggle for this today.
- **[~] Continue on CD-R — superseded, cyanrip-native.** Was done 2026-05-29 (pulled forward during T32) as whipper's `--cdr` flag (`Config.continue_on_cdr`, a "CD-R discs" Settings toggle, `RipParameters.cdr`, passthrough in `WhipperHostExportedImpl.rip()`); removed with whipper (KDD-18). cyanrip is cyanrip-native here too — no equivalent flag, no Settings toggle exists today.

- **[x] EAC gap-handling parity — CLOSED as already-satisfied (verified upstream 2026-07-21).** EAC's reference rip used **"Gap handling: Appended to previous track"**, and this was flagged (2026-06-14) as a possible parity lever because "we set no gap mode." Re-checked against cyanrip's own source and README (0.9.3.1 **and** master): cyanrip's default *is* EAC's — README §"Pregap handling": *"By default, track 1 pregap is ignored, while any other track's pregap is merged into the previous track. **This is identical to EAC's default behaviour.**"* We pass **no `-p`**, so the rip uses that default (exactly how the committed 12/14 audio-parity proof matched). So there is **no audio-parity gap here and no knob to add**: cyanrip's `-p` is a *per-track* override (`-p track_number=action`; `default`/`merge`/`drop`/`track`), not a global switch, and its only archival-safe value is the default we already use (`drop` deletes pregap audio and breaks cyanrip's no-discontinuities guarantee; `track` renumbers tracks and would desync our per-track `-t`/`-l`/progress/AR alignment). The **one** remaining EAC-gap difference is *cue-metadata only* — EAC's subchannel-detected `INDEX 00` pre-gap markers — which is **not** an audio-parity gap and is tracked separately (parity doc §Pregaps P3 + the cyanrip **PR #115** route in [docs/cyanrip-upstream.md](docs/cyanrip-upstream.md)). Same disposition as the udev/ReplayGain backlog closures: the feature was already delivered by cyanrip's default; the checkbox just hadn't been flipped.

Each is independent; do them in any order. They should land before the AppImage's first public release so the GUI matches what EAC users expect.

**Archival-quality follow-ups (from the 2026-06-23 EAC-guide gap analysis; see [docs/session-log.md](docs/session-log.md) + [docs/archive/archival-extraction-guide-2026-06.md](docs/archive/archival-extraction-guide-2026-06.md)):**

- **[x] cyanrip metadata richness (current-scope, "good everything"). Done 2026-06-23.** The MB lookup now also extracts **genre** (top folksonomy tag — musicbrainzngs 0.7.1 has no `genres` include), **disc number / total discs** (medium position/count), and **per-track ISRC** (`isrcs` include), and feeds them to cyanrip's `-a`/`-t` (FFmpeg `genre`/`disc`/`isrc`). Silent passthroughs (read from the stored MB `ReleaseDetail`, guarded by matching MBID; not editable). `RipMetadata.tracks` is now `TrackTag(number,title,artist,isrc)`; `ReleaseSummary`/`TrackSummary` gained the fields. whipper unaffected. **Composer deferred** (per-recording work→artist relationship queries = rabbit hole; revisit if a classical-heavy user asks).
- **[x] cyanrip FLAC encode-verify (archival integrity) — SHIPPED.** cyanrip encodes FLAC via FFmpeg with no decode-verify pass (unlike whipper's `flac --verify`). Closed by `adapters/flac_verify.py`: a best-effort, never-raising post-rip `flac --test` (decodes each FLAC and checks its embedded STREAMINFO MD5 against the decoded audio), run on the cyanrip output via the `verify_flac_after_rip` Setting (default on), wired in `main_window_rip._start_flac_verify` off the GUI thread. Result surfaced in the rip report + UI. (Doing this *inside* cyanrip is a separate, lower-priority upstream idea — see the cyanrip upstream-contribution list below.)
- **[x] FLAC compression level `-8` — whipper-only, shipped as an opt-in post-rip re-encode (2026-06-23).** whipper hardcodes flac `-5` (not exposable — KDD-13); `-8` is lossless and just smaller. **cyanrip is a no-op:** it encodes FLAC at *maximum* compression (upstream README "always uses maximum compression"; it sets libavcodec `compression_level` explicitly per format, not FFmpeg's default 5) and exposes no level flag — so there is nothing to expose or change there. Closed for whipper with an **optional post-rip re-encode** to `-8 --verify` (`adapters/flac_recompress.py`), gated on the new `WhipperBackend.produces_max_compression_flac()` capability (False=whipper→runs, True=cyanrip→skipped), surfaced as the "Re-compress FLACs" Settings toggle (off by default). Lossless + verified, atomic per-file swap-in, tags/art preserved; folded into the post-rip tag/cover thread so it runs after those. Flags (`-8 -e -p --verify --silent -f -o`) verified current against the xiph spec (2026-06-23). `-e` (exhaustive model search) and `-p` (exhaustive `qlp_coeff_precision` search) cost only *encode* time — never decode time, the one thing that mattered to the maintainer (mobile playback) — so they were added 2026-06-23 ("always fine to add encoding time if it helps") for the last fraction of a percent at zero playback cost. **Hardware validation gated:** test-plan **Test 10** (decoded-PCM MD5 identical before/after, cover art + tags survive, files smaller).

> **CTDB verify + repair are tracked elsewhere, not here.** They are archival-verification *features*, not parity-gap Settings widgets, so they live in the **Ranked execution order** above (items 5–6) with full rationale and decisions in the [Upstream open-source modification](#p1p2--upstream-open-source-modification-for-eac-parity-investigation-2026-06-02) section and [docs/archive/upstream-modification-investigation.md](docs/archive/upstream-modification-investigation.md). See also [PLANNING.md KDD-12 / KDD-14 / KDD-16](PLANNING.md).

### P1 — Release milestones

These remove most of the README's "until X happens" caveats. Done in order, they collapse Method C's friction substantially.

- **[x] Merge `claude/lucid-babbage-JYI8c` into `main`.** Done 2026-05-30 (`--allow-unrelated-histories`; main previously held only `.gitattributes`). Fresh `git clone` now lands on a working state. Removed the README dev-branch/authenticate steps and the `dev-setup.sh` branch-guard.
- **[x] Flip the GitHub repo to Public.** Done 2026-05-30 by the user. Plain `git clone https://...` now works without `gh auth login` / SSH key setup. The LICENSE decision it was gated on is also resolved: **GPL-3.0-only** (KDD-10) — `LICENSE` committed, `pyproject.toml` classifier set, README updated. Follow-up: drop the README Method-C "private repo, authenticate first" blockquote (see Documentation backlog).
- **[x] Tag `v0.1.0` and publish the AppImage as a release asset. Done 2026-06-01.** The first public release is live: [v0.1.0](https://github.com/rmccann-hub/Platterpus/releases/tag/v0.1.0) with `platterpus-x86_64.AppImage` (+ `.sha256`), `install.sh`, and `install-appimage.sh` all attached by `release.yml`. Both CI workflows (`ci.yml`, the new `appimage.yml`) and the release workflow are confirmed green on real Actions runs. Method A (AppImage) is now the recommended path. **Note:** the GitHub release got marked as a *full* release rather than a pre-release (UI default; `release.yml` only sets `--prerelease` when it *creates* the release, and this one was created in the UI). Cosmetic — flip it in the UI if a pre-release badge is wanted; future `git tag`-driven `v0.*` releases will auto-mark correctly.
      Earlier prep notes (2026-05-31): README rewritten for a published-AppImage world, `CHANGELOG.md` added, real app icon committed, release/CI workflows authored and YAML-validated.
- **[x] Publish the wheel to PyPI — DONE.** Method B is live: `pipx install platterpus` works. `.github/workflows/publish-pypi.yml` builds wheel+sdist, `twine check`s them, and publishes via **Trusted Publishing (OIDC, no stored token)** on each release, separate from `release.yml` so it can't block the AppImage. The one-time PyPI Trusted-Publisher config is in place and the publish run has gone green on every tagged release.

### P1 — Install automation

The host-side setup (Distrobox, container, whipper, exports) currently lives only in the README's prose. A reproducible script would catch the same pitfalls we hit walking the user through (`python3-setuptools` dep, `:latest` image pull confirmation, distrobox-export needs container entry). The post-clone side is already covered by `dev-setup.sh`.

- **[x] `setup-host.sh`.** Done 2026-05-30. Automates README Steps 1-4 (ensure Distrobox per-distro, create the `ripping` container with `--yes`, `dnf install whipper flac python3-setuptools` in-container, `distrobox-export` both binaries) **plus** clone + `dev-setup.sh` (Step 7). Idempotent (each step checks state first), with `--dry-run` (prints every command, changes nothing), `--yes`, `--no-gui`, `--container`, `--image`. Detects whether it's running inside a checkout (uses it) or piped from `curl` (clones to `~/Platterpus`). 7 smoke tests (`tests/test_setup_host_script.py`). **Untested against a real Distrobox host** — verified only via `--dry-run` + smoke tests in CI; needs a real-hardware run to confirm. Deliberately excludes drive calibration (GUI wizard) and Picard (GUI dependency manager).
- **[x] Document the curl-pipe-bash pattern** in the README as the "fast path" — done. The README quickstart leads with `curl -fsSL …/install.sh | bash` (and a download-then-run alternative); the manual Steps 1-4 are kept underneath as the source of truth.

### P1.1 — Install / uninstall ease (real-user testing)

Highest-priority subset of P1, focused specifically on the friction the first-time user hits between "no GUI installed" and "GUI running with a successful rip in hand." Items here unblock new contributors and reduce abandonment at the install step.

- **[x] ⭐ Zero-CLI distribution (PLANNING.md [KDD-17](PLANNING.md); user-approved 2026-06-04; ranked-order item 7). ALL THREE SLICES SHIPPED.** The headline install-ease goal: download one file, double-click, no terminal ever:
  - **[x] (a) Self-integrating AppImage — SHIPPED 2026-06-05** (`appimage_integration.py`; details in ranked-order item 7).
  - **[x] (b) Self-updating AppImage — SHIPPED 2026-06-09** (zsync update-information embedded at build; `.zsync` shipped per release; Help → Check for updates… delegates to AppImageUpdate or the release page; details in current-plan item 6).
  - **[x] (c) GUI first-run host wizard — SHIPPED 2026-06-05** (`deps/host_setup.py` + dialog + worker; cyanrip step added 2026-06-09; details in ranked-order item 7). Done since: the wizard exports `flac` (+ `metaflac`) from the container as of v0.3.5 (2026-06-27), needed by `flac --test` verification and the CTDB audio decode; CTDB verify was GUI-wired 2026-06-17.
  - **Rejected (see KDD-17):** Flatpak (sandbox can't reach host `~/.local/bin/whipper` — Critical Rule #3); a bespoke remote-config download stub (AppImage update-info already does it); a downloaded `.desktop`/script installer (Linux desktop trust model blocks it).

- **[x] Drive setup wizard (write-enabled) — top first-run priority.** Done 2026-05-30. Replaces the manual hand-edit of `whipper.conf` with a guided "Detect my drive" flow. `DriveSetupDialog` (Tools → "Set up drive…", and the Settings "Re-detect…" button) runs whipper's OWN `drive analyze` (cache) + `offset find` (offset) through the host-exported `~/.local/bin/whipper` on a worker thread (`DriveSetupWorker`), so they persist to `whipper.conf` themselves; we `back_up_whipper_config()` to `whipper.conf.bak` first. New adapter methods `analyze_drive()`/`find_offset()` (optional ABC capability — `NotImplementedError` default so non-whipper backends and test fakes still construct). Per-step failure is tolerated (a failed offset-find still reports the cache verdict). Also **fixed the "misleading read-offset field"**: it's read-only with the "Re-detect…" button beside it. Design: PLANNING.md **KDD-15**. 17 new tests.
  **Follow-ups:**
  - **[x] Manual-offset fallback — done 2026-05-31.** Real-user testing showed a fresh install with only CD-Rs is hard-blocked (whipper errors "drive offset unconfigured" and `offset find` needs an AccurateRip disc). The wizard now has a manual-entry spinbox + "Save offset" (linked to AccurateRip's offset list). It does **not** hand-author `whipper.conf` (still honouring KDD-15) — it persists via the GUI's existing `--offset` override (`Config.read_offset` + `override_read_offset`), emitted as `DriveSetupDialog.manual_offset_saved` and saved by the main window.
  - **[x] First-run auto-offer — done 2026-05-31.** On launch, if no offset is configured (new `offset_config.is_offset_configured()` checks `whipper.conf` *and* the override), the GUI offers the wizard once (dismissible; `Config.drive_setup_prompted` guards against re-nagging). Reversed the earlier "discoverable entry only" call after the CD-R block proved it's needed.
  - *Live streaming output during detection* — v1 shows a busy indicator + phase status; streaming the whipper output (like the rip view) is a polish item. Still deferred.

- **[x] Drive-access permission diagnostics.** Done 2026-05-30. New pure-stdlib `drive_access.diagnose_drive_access()` (injectable probes for testing) classifies the "no drive" state on the host: `no_device` (nothing connected), `permission` (a `/dev/sr*` node exists but isn't readable — owned by a group the user isn't in → fix command `sudo usermod -aG <group> $USER`), or `ok` (node readable, so the cause is elsewhere — container/whipper). `DrivePicker` now emits `drives_unavailable` on an empty refresh; MainWindow auto-shows the diagnosis **once per session and only when it's actionable** (a permission fix) — "no device" stays quiet (nothing to do). Always available via **Tools → Diagnose drive access…**. The dialog text is selectable so the fix command can be copied. Checking the host is correct because the AppImage runs as the host user and distrobox passes `/dev` through as the same user. (This was the one transferable lesson from the EAC-successor doc's Flatpak/Snap sandboxing section — the rest is N/A since we ship AppImage + pipx to reach host whipper.) 10 new tests.

- **[x] Auto-prompt the Unknown Album dialog when MB returns 0 matches.** Done 2026-05-28. Previously the user had to find File → Rip as Unknown Album in the menu after seeing "not in MusicBrainz"; now the dialog opens automatically the first time the GUI detects an unknown disc on a given drive selection. Guarded so it doesn't re-prompt if the user already accepted in this session.

- **[x] One-command uninstall script** (`uninstall.sh`). Done 2026-05-29. Default-removes the safe stuff (`.venv/`, `~/.config/platterpus`, `~/.local/share/platterpus`). Interactive prompts (or `--full`) for the broader cleanup: Picard Flatpak, the ripping Distrobox container, whipper.conf, host-exported binaries. `--dry-run` shows planned actions without executing. Music files at `~/Music/rips` are never touched without an explicit `--remove-rips` flag plus a typed `DELETE` confirmation in interactive mode. 6 smoke tests verify the script's help, error handling, and dry-run safety.

- **[x] One-command host bootstrap script** (`setup-host.sh`). Done 2026-05-30 — see the "P1 — Install automation" entry above for details. Remaining: a real-hardware run to confirm it (only `--dry-run`-tested so far).

- **[x] Surface install failures in the GUI summary popup** (verified done 2026-06-02), not only the log file. `MainWindow._show_dep_summary` appends an "Install failures:" block listing each failed dep + `InstallResult.message` (which `AutoInstaller` fills with the failing command's last stderr/stdout line), then points at the full log. Declines are excluded (the user already saw that dialog). Covered by `test_dep_summary_does_not_show_user_declines_as_failures`.

- **[x] Stop cascading the install dialogs when the user *declines*.** Done (verified 2026-06-02). `resolve_missing` skips cascade for `InstallResult.user_declined=True` (manager.py) — only real install *failures* cascade to the next tier. Both `AutoInstaller` (consent=No) and `QueuedInstaller` (empty selection) set `user_declined`. Covered by `test_resolve_missing_does_not_cascade_when_user_declines`, `test_resolve_missing_still_cascades_on_non_decline_failure`, and `test_dep_summary_does_not_show_user_declines_as_failures`.

- **[x] Version-stamp dependencies in the dep-report. Done 2026-06-02.** The probe already reads each dep's version; `DependencyReport` now carries `ok_versions` (dep_id → detected version), `check_all` populates it, and the summary popup lists an "Installed: whipper 0.10.0, FLAC 1.4.3, …" line (a version-less-but-present probe renders as "unknown"). New `version.format_version()` helper. Tests across `test_deps_version`, `test_deps_manager`, `test_ui_main_window`. *(Not done: pinning the Picard `.flatpakref` to a fixed version — that always tracks latest by URL; left as a separate question since pinning a Flatpak ref is non-trivial and the version is now at least visible to the user.)*

### P1 — UX gaps from real-user testing

Items that surfaced when an actual user walked through the GUI on Bazzite. Each is small but each makes the first-run experience noticeably worse.

- **[x] Show placeholder track rows for an unknown disc.** Done 2026-05-29 (T32). Previously the track table stayed empty when MusicBrainz had no match, so the user couldn't see what was on the disc before an unknown-album rip. whipper reports the track count even for an unidentified disc, so the adapter salvages it from `cd info`'s partial output (`DiscInfo.num_tracks`) and the main window renders that many rows via `TrackTable.set_placeholder_tracks()` — pre-filled with `Track 01`…`Track NN` titles + `Unknown Artist`, and album fields set to `Unknown Artist` / `Unknown Album` to mirror the tags the rip writes. The no-match handler is shared by the empty-disc-ID path and the 0-result-lookup path. **Follow-up is P2 (below):** edits to those rows don't yet feed the unknown rip.

- **[x] Live status during the pre-track disc scan.** Done 2026-05-29 (T32). The status label sat on "Starting rip…" for the whole initial TOC/table read (a minute-plus) because those whipper lines carry no track number, so the GUI looked frozen. `RipWorker` now emits a `status(str)` phase signal (`_describe_activity`) recognizing the disc-scan, per-track read/verify, encode, tag, and length phases; `RipProgress.set_progress` drives the bar only while `set_status` owns the label.

- **[x] Default path template → Artist/Album folders + per-mode templates.** Done 2026-05-29 (T32). Replaced the flat v1 `Artist - Album/` layout with two template pairs, picked per rip in `ui/rip_controls`:
  - **Known disc:** `%A/%d/%t - %n - %d - %A - %y` + disc `%A/%d/%d` → `Artist/Album/01 - Title - Album - Artist - Year.flac`.
  - **Unknown disc:** literal `Unknown Artist/Unknown Album/%t - Track %t` + disc `Unknown Artist/Unknown Album/Unknown Album` → clean `Unknown Artist/Unknown Album/01 - Track 01.flac`. This is what made the "Unknown Album now" choice safe — whipper never sees `%d` (the disc-ID hash) for unknown discs, so no post-rip renaming and no broken `.cue`/`.log` references.
  - All four templates are editable in Settings. Config schema bumped to v2 with a migration that upgrades the known templates only if they still hold the v1 defaults (hand-edited templates preserved); the unknown templates fill from defaults when absent.
  - **Flat-template caveats (documented in config.py):** a known disc with no year leaves a trailing " - " (whipper can't conditionally omit an empty field); disc-number/volume (`%N`) is always present so it's left out of the default — add `/%N` for multi-disc sets.

- **[x] Highlight the current track row during a rip. Done 2026-06-02.** The track table now follows whipper track by track. Note the mechanism changed: `RipWorker.progress` was reworked to `(overall, task)` percentages and no longer carries the track number, so this added a dedicated `RipWorker.current_track(int)` signal (emitted once per new track, derived from the `"track N of M"` lines the worker already parses) wired to `TrackTable.highlight_track()` (selects + scrolls the row; out-of-range numbers ignored). Tests: `test_emits_current_track_once_per_new_track`, `test_highlight_track_selects_matching_row`, `test_highlight_track_ignores_out_of_range`.
- **[x] Read offset field in Settings is misleading.** Resolved 2026-05-30 by the drive setup wizard (P1.1 / KDD-15): the field is read-only and now sits beside a "Re-detect…" button that launches the wizard — the supported way to (re)calibrate and write the offset to `whipper.conf`. (Still open as polish: parse `whipper.conf` to *display* the live per-drive offset rather than our config's stored copy.)
- **[x] PendingInstallsDialog visual feedback during install. Done 2026-06-02** (chose option 1: the dialog drives the install loop itself). `PendingInstallsDialog` now takes an optional `install_one` callable; when supplied, clicking "Install Selected" installs each ticked item in turn, updating that row live (`installing…` → `OK`/`FAILED`) then swapping in a Close button, with `results()` exposing one `InstallResult` per item (unticked → `user_declined`, so the manager won't cascade them). A new GUI resolver `main_window._DialogQueuedResolver` replaces `QueuedInstaller` in the GUI path (QueuedInstaller installs *after* its callback returns, which closed the dialog); `QueuedInstaller` itself is untouched and still used elsewhere. Row repaint uses `widget.repaint()`, NOT `QApplication.processEvents()` — the loop runs as a slot inside the modal `exec()`, and processEvents would re-enter that loop / pump unrelated timers+threads (a crash hazard caught in testing). Passive (no-`install_one`) mode preserved for existing callers/tests. Tests in `test_ui_pending_installs_dialog` + `test_ui_main_window`.
- **[x] Declined dependencies should not cascade to the next tier.** Done (verified 2026-06-02) — see the identical item under P1.1 above. `resolve_missing` skips cascade for `user_declined`; three tests cover it.
- **[x] Picard auto-install failure mode — resolved.** Both halves are done: (1) **root cause** — the registry now installs Picard via the **`.flatpakref` URL** (`https://dl.flathub.org/repo/appstream/org.musicbrainz.Picard.flatpakref`) instead of `flathub <ref>`; the `.flatpakref` carries the remote URL so flatpak adds flathub at *user* level on first install, fixing the Bazzite "No remote refs found for 'flathub'" error (Atomic distros configure flathub as a *system* remote). See `deps/registry.py`. (2) **diagnostics** — `AutoInstaller` captures the failed command's last stderr/stdout line into `InstallResult.message`, and `_show_dep_summary` surfaces it in an "Install failures:" block (no longer debug-only). Picard is also `optional=True`, so a failure doesn't nag.

### P0 — Exhaustive argument documentation + black-box limit testing, our half (2026-08-06)

Maintainer, and it is now `docs/seam-rules.md` **S-8/S-9/S-10** (version 2): *"i want it exhaustive on you side and on thiers. even if you dont use the argument or variabe or setting, i want i documented and with the limits and errors. we may have to use or fix in the future."* Plus the division of labour: *"i dont expect you to test cyanrip, its on them, just like its on you."*

**What we owe, and it is a real body of work:**

- **[ ] Rows for all 41 of their flags, not our 17.** For every flag we do not send, the row must say `NO: <reason>` or `?`. Today nothing distinguishes *"we decline it"* from *"we never noticed it"* — and those are different facts about the same blank cell.
- **[ ] Black-box limit probes for every argument we DO send**, run against the real binary rather than read out of the builder: the **real** accepted min/max (the declared type is not the range — `int` says nothing about whether `-1` is taken); behaviour at min, at max and **one past each**; and on a bad value the exit code, the message, and **whether the operation dies or the flag is silently ignored**. That last distinction is the difference between a bad tag and a lost rip: `-t 17=` on a 16-track disc killed a rip in two seconds and the *type* was fine.
- **[ ] The same for our own surface** — every `Config` field and every CLI flag, including ones the GUI cannot set. Same columns, same rule.
- **[ ] `not-probed: <reason>` where hardware or a specific disc is required.** A recorded finding. **A blank reads as "tested and fine"**, which is the failure the file exists to prevent.
- **[ ] Interactions**: `-I` must never appear with `-J` in our builder and **neither of us has recorded why**; `-F` is in the builder with no recorded reason at all. Probe both, document both, or delete them — carrying a flag we cannot explain is worse than not having it.
- **[ ] Generate, do not transcribe.** The type/range columns in `docs/seam-commands.md` are currently hand-written and carry a provenance warning saying so. `emit_dependency_contract.py` must emit them from the builder's signatures and range checks, and the probe results must land beside them mechanically.

The limit probes are a natural fit for the in-app script runner once `cyanrip`/`expect-exit` are joined by the rest of the vocabulary — a generated batch that walks every argument to its boundary and records the exit code is exactly the artifact S-9 asks for.

### P0 — The command table must be AUDITED every round, and the gate change is bilateral (2026-08-06)

The maintainer: *"it needs to be looked at, checked, and verified, every time there is a handshake, its most of the entire point."*

Correct, and a shared table nobody re-reads is the same artifact as no table — this protocol has already paid for exactly that once: their flag table said `-v`/`--version` with **no `-V`** for a full round while every version probe we shipped sent `-V`, and a rejected flag exits non-zero, which every probe reads as *"the tool is not installed"*. **The document was right; nobody looked at it against our code.**

**The mechanism is designed, prototyped and measured — and then deliberately reverted**, because landing it unilaterally would have been wrong:

Add `SEAM-COMMANDS` to `REQUIRED_CLOSE_FIELDS` in `scripts/handshake.py`, with a **value** check, not just presence:

| declared | result | why |
|---|---|---|
| `SEAM-COMMANDS: audited @ 1` | closes | the round names the table version it audited |
| `SEAM-COMMANDS: not-audited` | **blocks** | an honest answer, and it must stop a close — *"we did not look"* has to stay distinguishable from *"we looked and it was fine"* |
| `SEAM-COMMANDS: looked at it` | **blocks** | an unrecognised value is treated as not-audited, never waved through — a check that passes on a value it does not understand is satisfied by the wrong thing |
| *(absent)* | **blocks** | a missing field cannot express an audit |

All four verified against the real `close_blockers` before the revert.

**Why it was reverted rather than shipped:** `tests/test_handshake_tooling.py::test_the_required_field_set_matches_the_published_spec` failed with *"SEAM-COMMANDS is required by our gate and absent from the shared docs/handshake-protocol.md — one of the two has drifted."* **That test is doing its job.** `handshake-protocol.md` is the file *neither project owns*, and rule #12 is explicit: editing it is a version bump **both sides must ship before the next close**. A gate demanding a field the shared spec does not define would reject the fork's conforming files — we would have broken their side to tighten ours.

- **[ ] Propose the protocol version bump in round 8**, with the four-row table above as the specified behaviour, and land the gate change **in the round where both sides adopt it** — not before.

### P0 — There is no single shared command/type/meaning table, and ours has no types at all (2026-08-06)

The maintainer: *"do you and cyanrip both have a singurlar table for both of your commands, type, arguements, and meanings? because you should and it should be a file both have and check every time via the handshake. and it should be audited by both sides every time completely."*

**Answer: no, and checking made it worse than expected.**

What exists today is **two half-contracts plus a hand-written gloss**:

| artifact | who generates it | what it carries |
|---|---|---|
| `docs/cyanrip-consumer-contract.md` §3 | us, from a real call to the argv builder | **18 bare flag names.** No types, no arguments, no meanings |
| their `PROVIDER-CONTRACT.md` §P1 | them, from the binary's own `--help` | 41 flags, 82 spellings |
| `docs/dependency-contracts.md` | **a human, by hand** | the per-flag semantics our §3 explicitly punts to |
| `tests/test_argv_surface_agreement.py` | — | compares flag *names* only, one direction |

Three defects fall out, and the third is the one that matters:

1. **Our half carries no types.** §3 is a flag list that says *"Per-flag semantics and the exact contract for each are in `docs/dependency-contracts.md`"* — i.e. it delegates the substance to a **hand-maintained** file, which is the exact artifact class this project keeps finding stale (`docs/testing.md` §5.af). A generated contract that punts its semantics to a hand-written one is generated in name only.
2. **41 versus 18.** They document 41 flags; we send 18. Nothing states, per flag, whether we deliberately do not use it, cannot use it, or have not noticed it. "We send these 18" and "these are the 18 worth sending" are different claims and only the first is recorded.
3. **The comparison is one-directional and name-only.** Our test diffs our names against their table. Nothing diffs *their* table against *our* needs, and nothing compares **types or argument shapes at all** — so a flag whose argument changed from an int to a string would pass the existing check silently.

**The design, and it must not be hand-authored.** One shared table, `docs/seam-commands.md`, at the same path in both repos — but **merged by a tool from both generated halves**, never written by a person. That keeps the property rule #12 exists for (*a description derived from the behaviour cannot describe behaviour we do not have*) while giving the single artifact he is asking for. One row per flag:

`flag | spellings | argument type | value range | meaning | we send it? | they accept it? | last agreed round`

- Generated by extending `scripts/emit_dependency_contract.py` to emit **types and ranges** (it already calls the real argv builder — the types are in the builder's signature and the range checks are already in the code), then joining against their published table.
- **Every row gets a status from each side**, so `we-send / they-accept` disagreements are visible as rows rather than discovered as a broken release. `-V` is the worked example: their table said no `-V` for a full round while every probe we shipped sent it, and only a human reading both files caught it.
- **Audited by both sides every round**, completely — the handshake gate fails when a row's status is `not-audited-this-round`, so "we did not look" is distinguishable from "we looked and it was fine".
- **`docs/dependency-contracts.md` gets absorbed or demoted.** It cannot remain the authority for semantics while a generated file exists; two descriptions of one thing is the drift this fixes.

- **[ ] Extend the emitter to carry types + ranges; build the merge; add the both-sides-audited gate; propose the shared file in the round-8 outbound alongside `docs/seam-rules.md`.**

### P0 — The script vocabulary advertises 13 verbs the runner does not implement (found 2026-08-06)

**Verified by running it, not by reading it:** `verbs.py` advertises **25** verbs; `runner.py` implements **12**. The other **13** parse cleanly, pass the arity check, pass the unsafe gate, and then fail at *run* time with `'<verb>' is not implemented yet` — `set`, `expect`, `expect-contains`, `album`, `album-artist`, `rescan`, `rip`, `wait-for-rip`, `cancel-rip`, `expect-status`, `expect-tracks`, `eval`, `call`.

**This is `docs/testing.md` §5.p — "a documented capability is not a capability" — committed by the person who wrote that rule down.** The built-in reference renders from the verb table, so the console would show a user thirteen commands that cannot run. A batch pasted against that reference dies mid-run, unattended, which is the precise failure the whole feature exists to prevent.

- **[ ] Either implement the thirteen or mark them unavailable in the table**, and add the sweep that makes the two halves agree — `set(VERBS) == {handlers on ScriptRunner}` is a one-line assertion and it would have failed the moment the gap opened.

### P0 — `set`/`expect` must key on Config field names, NOT row labels (audit, 2026-08-06)

`verbs.py` currently says *"set `<field>` `<value>` — set a Settings field by its row label."* **That is the wrong design and the audit gives three in-repo proofs:**

1. **Seven form rows have the label `""`, five of them interactive** — `override_read_offset`, `notify_on_completion`, `save_additional_art`, `rerip_offset_variant`, `secure_rerip_dynamic`. There is no label to address them by, so a label-keyed namespace cannot reach five real switches.
2. **Labels are prose and they get renamed.** `option_labels.py` exists *because* every option string was renamed in b11 — a script pinned to `"Fixed speed (advanced)"` broke silently at that commit.
3. **A registry already exists, half-built:** `settings_dialog.py:700`'s `_validated_widgets: dict[str, QWidget]` already maps **config field name → widget**, for 8 of them. Generalising it gives `set`, `expect`, the validation renderer and the completeness test **one** source.

So: **canonical key = the `Config` field name; row label = an alias**, matched by equality after normalisation (never `startswith`/`in`), with ambiguous or empty aliases **refused at parse time** rather than guessed.

- **[ ] Traps the audit found that any resolver must handle**, each of which would otherwise be a silent wrong answer:
  - `secure_rerip_dynamic` is **INVERTED** relative to its checkbox; `update_channel` is a **bool view of a string**.
  - `Read offset (samples):` names **two** widgets (the spin box and `Re-&detect…`) — the input must win or the resolver must refuse.
  - Substring collisions: `Track template:` ⊂ `Track template (unknown):`; `Verify FLACs:` and `Re-compress FLACs:` share `FLACs:`.
  - Unicode that will not survive a copy-paste: `×` is **U+00D7** (not ASCII `x`) in `Fixed speed (×):`; `…` is **U+2026**.
  - Mnemonic ampersands survive `.text()` — `Chec&k dependencies`, and `&&` renders as one `&`.
  - `metaflac path:` is the only lowercase-initial label; an over-eager `.title()` normaliser eats it.
  - `recompress_flac_after_rip` is **permanently disabled**; `mp3_vbr_quality` and `read_speed` are **gated** — setting a disabled widget must FAIL loudly, not no-op silently.
- **[ ] The completeness test:** derive the editable set from the dialog and assert every one is addressable, so this audit cannot silently expire.

### P0 — The RETURN path from cyanrip is unsanitised, and Qt's default renders it as HTML (found 2026-08-06)

The maintainer asked the mirror of the argv question: *"do all logs and commands pass back to platterpus from cyanrip before user facing? same deal, they probably should and get sanitized and checked ... this should be a check in both directions, and full."*

**Measured answer: the output half has no sanitiser at all.** Two greps settle it:
- `grep -rn "setTextFormat|Qt.RichText|Qt.PlainText" src/platterpus/ui/` → **zero hits.** No widget anywhere pins its text format.
- No sanitiser function exists on the return path (`ripper_messages.py`'s `re.escape` calls are regex construction, not output cleaning).

**Why that is a live defect, not a theoretical one.** Qt's default is `Qt::AutoText`, which **auto-detects HTML and renders it as rich text**. cyanrip's `captured_stdout` and `failure_hint` reach user-facing surfaces (`main_window_rip.py:1368`, `:1456`). So any captured line that *looks* like markup is interpreted rather than shown.

**The realistic failure is silent text loss, not an exploit.** cyanrip is a local trusted binary — but the *content* it echoes is not ours: album and track titles come from **MusicBrainz**, i.e. from outside. A title containing `<` — `Track <Remix>`, `A > B`, `<untitled>` — is swallowed as an unknown tag in a user-facing error dialog, and **the user never learns text went missing**. That is exactly CLAUDE.md's *validate every dependency output* category and exactly the silent-truncation shape the diagnostic-completeness rule exists to forbid.

- **[ ] Pin every user-facing widget that can carry dependency output to `PlainText`**, and add a sweep test asserting no `QLabel`/`QMessageBox` receiving tool output is left on `AutoText`. The sweep matters more than the individual fixes — this is a rule to enforce across the codebase, not at the one place it was found (`docs/testing.md` §5.o).
- **[ ] Add the return-path sanitiser as the mirror of `sanitise_cyanrip_args`**: strip/flag control characters and NULs, bound absurd line lengths (a 10 MB single line will freeze the GUI thread rendering it), and preserve everything else verbatim. It must **never silently drop** — an elision is counted and marked, same rule as the argv side.
- **[x] Institutionalised in both repos.** The clause is now a bullet of Critical rule #12 in `CLAUDE.md` (which is the bidirectional-seam rule and already carries the "this rule lives in both repos" obligation), and the fork's half is drafted ready to send as [`docs/handshake/verified/round-07-lap-29.md`](docs/handshake/verified/round-07-lap-29.md) §S. That file describes **our own two defects** rather than proposing a clause from a clean position, asks which of their routes reach the ripping core, and asks for confirmation the clause landed on their side so the next round can cite it instead of re-arguing it.
- **[ ] Make it a two-way contract test.** The input half is `tests/test_argv_surface_agreement.py`. The output half has parser tests but nothing asserting *what reaches the user* is what cyanrip said. That asymmetry is the same one that let the `-V` blocker ship for a full round.

### P0 — Handshake lap 28: our sent verdict is wrong on both halves (verified 2026-08-06)

**Our lap 27 is sitting in the fork's inbox making two false statements**, both verified against committed artifacts rather than remembered:

- **[ ] The HOLD's only stated reason has evaporated.** Lap 27 line 20 declares `**HOLD on f5e11ba**` because *"the P1 flag table still has not arrived"*, and line 297 says our argv check is *"diffing our argv against **round 6b's** table"*. Both false today: `docs/handshake/inbound/artifacts/round-07-lap-25-provider-contract-g9048082.md` exists (738 lines, 45 KB, 2026-08-05 18:51), and `tests/test_argv_surface_agreement.py` has `_MAX_TABLE_LAG = 0` and passes — it reads round 7's own table.

- **[ ] Lap 27 recommends a pin our own product has retired.** Line 285: *"**No pin change requested.** `f5e11ba` remains our test pin and our recommendation."* Meanwhile `deps/fork_source.py:200` has `FORK_TEST_PIN = "9048082"` and line 252 lists `"f5e11ba"` in `SUPERSEDED_TEST_PINS`. The wizard installs `9048082`; the handshake file recommends `f5e11ba`. **The code and the contract disagree about which binary we want**, which is exactly the class of drift rule #12 exists to prevent.

- **[ ] Root cause, and it is theirs: lap 25 was sent THREE times under one lap number.** Protocol §2 is unambiguous — *"Each lap is a new file. Never edit a file already sent."* On disk: `superseded/round-07-lap-25-as-first-sent.md` and `…-as-second-sent.md` both carry `HANDSHAKE-TEST-PIN: f5e11ba`; the live `inbound/round-07-lap-25.md` carries `HANDSHAKE-TEST-PIN: 9048082` and attaches the contract. **Our lap 27 was written against the second send.** So it is a faithful reading of a document that was replaced under the same name — which is the precise failure §2 forbids, and it needs raising as an ask, not as a complaint.

- **[ ] Second-order finding worth more than the first:** the table arrived and *our own check still could not see it* for a further lap, because `_group_by_round` globbed only lap files and the shared round parser returns `None` for an artifact filename (fixed in `8a045ab`). **A contract sitting in a directory nothing reads is not a contract received.** Already graduated; restate in lap 28 because it is the transferable half.

- **[ ] Also stale in lap 27, by construction:** `HANDSHAKE-APP-VERSION: platterpus 0.6.4b8` (now b11), and §F cross-references §G ("Revert-proof") for the flag-table blocker that actually lives in §K — a reader following the pointer lands in the wrong section.

**Still true in lap 27 and to be re-asserted rather than re-derived:** the consumer-contract counts (55 parsed / 17 ignored / 18 flags) survive regeneration at b11; the drive-proven A1/A2/`--verify-log` rows stay citable *scoped to `f5e11ba` + b6/b7/b8*; and the standing caveat that nothing here exercises a *stock* cyanrip.

**Lap 28 must not claim** anything needing rig data we do not hold — in particular it cannot approve `9048082` on evidence, because no disc has been ripped on it yet. Their own §E1 says they are not asking us to approve it untested.

### P1 — Rig-session findings, 2026-08-05 (b10 + cyanrip `9048082`) — SHIPPED in v0.6.4b11

Raised by the maintainer while walking through the b10 build on the Bazzite rig, recorded first and acted on after his go-ahead (*"only options, roll a new version if needed after ingesting all this data"*). Every claim below was verified against the code *before* being written down, because two of the five turned out not to be what the screenshots suggested — and those two are marked as **refuted**, not fixed.

- **[~] The naming ask — DONE for the option labels; the `[Debugging]`-on-the-Goal-row half is still a decision for the maintainer.** Shipped in v0.6.4b11: `option_labels.py` defines the one convention (`Name — Descriptor In Title Case [Qualifier]`) with a pure `check_option_label()`, and `tests/test_option_labels.py` sweeps every item of every combo in the *constructed dialog* — not a table of the labels we know about — so a sixth dropdown is covered without anyone remembering. Pinned non-vacuous by a test asserting all 19 pre-rename labels fail the checker, and by one asserting every combo still carries the same item data. `naming.CUSTOM_LABEL` is now the shared constant. **What is deliberately NOT done:** annotating the *Goal* row with state no preset owns (his `[Debugging]` example). That needs a decision on which fields a label may speak for, and `docs/rig-session.md` §1 asks him for it.

  Original ask: Maintainer's words: *"These settings should be called something like Flack - Lossless Archival Master [Debugging] or similar, and other settings should reflect similar naming syntax."*

  **The "auto-change to Custom" half of the request already works, and that is verified rather than assumed** (`goal_presets.py:85-89`, `settings_dialog.py:67-70`, `_on_dependent_changed` at `:940-946`; run offscreen against the real dialog: all six preset-driven controls flip the combo to `Custom (hand-tuned below)` immediately, `to_config().rip_goal == "custom"` persists it, and a config matching no preset re-opens showing Custom. Pinned by `test_editing_a_control_flips_goal_to_custom` and `test_every_goal_preset_field_has_a_wired_control`).

  **So what he is actually asking for is different from what it looks like.** His screenshot shows `Archival exact` while **Debug logging is on** — and debug logging is *not* a goal-driven field, so nothing is wrong. He wants the label to describe state the preset does not cover. That is a design question, not a bug: decide which fields a label may mention, and whether a `[Debugging]`-style suffix is a *label* or a separate status line. Scope for a rename: `GOAL_LABELS` is the single source for the three presets, but `"Custom (hand-tuned below)"` is a **hardcoded literal** at `settings_dialog.py:70` that duplicates `naming.CUSTOM_LABEL` (used by the unrelated naming-scheme combo — renaming naively renames both), and the labels are restated by hand in `help_content.py:169-173`, `README.md:11`/`:548`, `PLANNING.md:151`/`:310`, `docs/ux-design-principles.md:46`/`:110`, `docs/test-plan.md:725`.

- **[x] One genuine defect found while checking the above: the Goal combo ignores the persisted `rip_goal`.** **FIXED in v0.6.4b11** — resolved in favour of *the fields are authoritative, the label is a view of them*, which is `detect_goal`'s documented semantics. `rip_report.build_settings` now derives `settings.rip_goal` through the same function the dialog uses, and keeps the stored value as `settings.rip_goal_stored` **only when the two disagree** (report schema v23) — discarding a disagreement silently would be the same class of bug in a smaller place. Five regression tests, and the revert was applied-and-proved before believing the run. `_wire_goal_presets` re-derives from the field values via `detect_goal` and never reads `config.rip_goal`, so a saved goal can disagree with what the dialog shows (measured: `Config(rip_goal="custom")` with default fields re-opens as `fast_verified`). Harmless today because the derived answer is the truthful one — but the report writes `settings.rip_goal` into every rip's JSON, so the *record* can name a goal the settings never matched. Decide which is authoritative and make the other follow.

- **[x] The dependency dialog truncates the ripper version and names no commit. CONFIRMED, and it is captured-and-discarded.** **FIXED in v0.6.4b11** — `BuildNote` gained `version_text` and `build_tag` (both read off the `RipperIdentity` the dialog already receives) plus an `identity_line()` renderer, so the row now reads `cyanrip 0.9.4-rc1+platterpus.5-beta.5 (the Platterpus fork; build tag "platterpus-fork-g9048082")`. The `; build tag "…"` shape rather than `, build …` because the unknown-build summary is literally the words "build not identified", and a comma there produced "build not identified, build g1a2b3c4". It shows `cyanrip 0.9.4 (the Platterpus fork)` where the binary's own banner is `cyanrip 0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)`. Two independent losses: `deps/version.py:33-35` reduces the version to an int triple, so `-rc1+platterpus.5-beta.5` is structurally unrepresentable, and `build_notes.py:100-107` collapses the build to the four-word phrase `"the Platterpus fork"`. **Both the full banner and the build tag are live in the object the dialog receives** (`probe.raw_output`, and `identify_from_banner().build_tag`) — so this is the exact shape `CLAUDE.md` names: *"our dependency dialog reading `cyanrip 0.9.3` / `0 missing`: every word accurate, the message wrong."* It is also rule #12's *say which build* obligation unmet on the surface a user actually reads.

- **[x] The setup-wizard rows name no build either. CONFIRMED.** **FIXED in v0.6.4b11** — `_title_for` / `_done_detail` / `_ran_detail` on `HostSetup`; the row reads `… — commit 9048082` with `already present — the installed banner names commit 9048082`. Worded to match what `_fork_installed` actually checks (the tag *contains* the pin) rather than claiming an equality nobody tested. The fork row renders exactly `✓ Platterpus fork of cyanrip (build + export) — already present` (or `— installed`); `host_setup.py:451-463` titles, `:514`/`:591` details. **The `ForkTarget` is already read inside the very probe that produces that row** (`host_setup.py:294-295` reads `self._target.pin` to decide "already present"), and it exposes ready-made `build_tag` / `banner` / `why` strings that no UI consumes. So the row can say which commit it checked for at no new cost.

- **[x] The release picker logs nothing at all, so a wait for input is indistinguishable from a hang.** **FIXED in v0.6.4b11, and fixed on the shared base rather than at this one call site** (`docs/testing.md` §5.o). `CenteredDialog` now logs `dialog presented:` from `showEvent` — which makes the line *evidence Qt mapped the window*, a stronger claim than a line before `exec()` — and `dialog closed: … — accepted / rejected or closed` from `done()`, the single funnel accept/reject/Esc/WM-close all route through. The picker additionally logs the candidate count, the words "this is not a hang", the elapsed wait, and the chosen mbid; the accepted-with-no-selection branch is a WARNING rather than a silent return, because a silent return there reads exactly like a cancel. Nine tests across two files, including a floor asserting the single-match path emits *none* of these lines — otherwise the others would be satisfied by one `log.info` at the top of the method. The maintainer closed the app because it *"looked hung"*; the log has a **96-second silence** (19:36:41 → 19:38:17) and the main window was showing `MusicBrainz match: 4 matches found — pick one`.

  **The mechanism I first suspected is refuted:** a modal wizard/message box cannot swallow the picker, because the MB result arrives as a queued cross-thread signal and nested Qt event loops still deliver those. But `main_window.py:1090-1099` calls `dialog.exec()` with **no log line on any branch** — not opened, not waiting, not accepted, not cancelled — and `disc_info_panel.py` does not import `logging` at all. **So a 96-second silent gap is exactly what this path produces whether or not the dialog was visible, and the artifact cannot tell us which happened.** That is the finding: not "the picker was hidden" (undetermined), but "we cannot answer the question from the log". Log the picker's lifecycle first; only then is a hidden-dialog claim checkable.

- **[x] My own instruction was wrong: `./platterpus-x86_64.AppImage --install-ripper 9048082` fails after the app relocates itself.** **DONE in v0.6.4b11** — `README.md` → *Command-line usage* now opens by saying where the file actually is and that a `./` command from the download folder will report *No such file or directory*; the `--install-ripper` example uses the `~/Applications/` path; the same note is in `docs/test-plan.md` §A3 and `docs/hardware-test-checklist.md`. The AppImage is **moved** (`shutil.move`, `appimage_integration.py:93`) to `~/Applications/` — but only after an explicit Yes, and the app *does* name the new absolute path in a follow-up dialog (`main_window_provision.py:192-199`). So the app behaved correctly and the docs did not: sweep every bare `./platterpus-x86_64.AppImage …` command in `README.md` and `docs/` and make them relocation-safe. Also worth noting for the record: the b10 wizard built `9048082` on its own, so the manual step was never needed.

### P1 — Trust & supply-chain hardening (2026-07-08 audit follow-ups)

From the trust/quality deep audit — see [docs/archive/trust-audit-2026-07-08.md](docs/archive/trust-audit-2026-07-08.md). Confirmed-but-deferred items (the audit's in-release fixes shipped in v0.4.22):

- **[~] ⭐ Update authenticity (trust-critical).** **Build-provenance attestation DONE** — `release.yml` runs `actions/attest-build-provenance` over the released AppImage (SLSA, GitHub OIDC + Sigstore, no key/secret; verify with `gh attestation verify … --repo rmccann-hub/Platterpus`), and PyPI wheels are attested via Trusted Publishing. **The verify side DONE 2026-07-21 (KDD-26):** the must-ask was answered and `cryptography>=50.0.0,<51` is a declared runtime dep ([DEPENDENCIES.md](DEPENDENCIES.md)); `src/platterpus/update_signing.py` (`verify_minisign`, `verify_minisign_file`, `signing_configured`) is wired into `update_install.py` **fail-closed** on a present-but-invalid signature, with tests. It is dormant because `update_signing.PUBLIC_KEY_B64` is empty — today's gate is SHA-256 only, which `SECURITY.md` documents honestly. **Remaining, maintainer-only:** generate the keypair, bake in the public key, sign the first release — the ritual is in [docs/architecture.md §6.2](docs/architecture.md).
- **[x] Pin GitHub Actions to commit SHAs** — DONE (round 2, 2026-07-08): every `uses:` across `ci.yml`/`release.yml`/`publish-pypi.yml`/`appimage.yml`/`mutation.yml` pins a full commit SHA (`# vN` comment). Dependabot (`github-actions`) drives the bumps.
- **[~] Reproducible AppImage build.** **`SOURCE_DATE_EPOCH` — DONE (2026-07-08):** `build_appimage.sh` pins every embedded timestamp to the HEAD commit time; verified the *wheel* is byte-identical across rebuilds (same sha256). **`pip --require-hashes` dependency byte-pinning — PLUMBING SHIPPED (2026-07-21, Option A, maintainer-chosen):** the python-appimage-compatible design is a **hash-verified wheelhouse** — `build/lock-requirements.sh` resolves the third-party closure and writes a hash-pinned `requirements.lock` (run in the release env when a dep changes); `build_appimage.sh`, *when the lock exists*, `pip download --require-hashes`-es the closure into a local wheelhouse (aborts on any byte mismatch) and installs python-appimage's per-line deps **offline** from it, with the local `platterpus` wheel served alongside. It's **opt-in and additive** — no lock ⇒ the previous version-pinned online install, unchanged. Parsing logic unit-verified; scripts `bash -n`-clean. **Still gated on a real build (only place it can be validated):** generate the lock in CI/the release env, commit it, and confirm the *full* AppImage is byte-identical across rebuilds (the sandbox can only verify the wheel half).
- **[x] Static type-checking in CI — DONE (whole package strict, 2026-07-20).** `mypy` in the `dev` extra + a gating CI `typecheck` job. Ratcheted up in stages: non-UI package (2026-07-09), standalone UI widget/dialog modules (2026-07-10), then the final six `main_window*` god-object modules (2026-07-20). `disallow_untyped_defs` + `disallow_incomplete_defs` are now enforced across the **entire package with no `ignore_errors` exclusions left**. The last step needed a **shared typing seam** (`ui/main_window_shared.py::MainWindowShared`): the mixins' `self` is the concrete window at runtime but the bare mixin to mypy, so cross-mixin `self._x` couldn't resolve (the bulk of the 317 errors were `attr-defined`). The seam is a type-only declaration of the window's shared surface (attrs/signals/cross-mixin methods) that every mixin inherits; it's runtime-neutral (bare annotations + `TYPE_CHECKING` method stubs + a `TYPE_CHECKING`-conditional `QWidget`/`object` base — see docs/architecture.md §3.6). Along the way, ~10 residual real type-gaps were fixed properly (retyped `object|None` workers to concrete classes; `_build_gui_dependency_manager -> DependencyManager`; typed the unknown-post-processing album/track params; widened two `list[object]` helpers to `Sequence[object]`). Full suite green; MRO/metaclass verified unchanged at runtime.
- **[x] `pip-audit` CI job** + **scheduled `mutmut`** + warn-only "src changed without tests" check — DONE (round 2, 2026-07-08): gating `pip-audit` job in `ci.yml` (currently clean), weekly non-blocking `mutation.yml` (`mutmut` over `parsers/`, `verdict.py`, `ctdb/crc.py`), and the advisory `tests-touched` job.
- **[x] Known-disc re-rip overwrite confirm — DONE (2026-07-08).** A known-disc rip whose target album folder already holds audio now shows a **Replace / Rip to a new folder / Cancel** dialog instead of silently overwriting. Pure helpers (`known_album_folder` renders the disc template the way cyanrip does; `suffix_album_folder_template` / `free_album_folder_templates` land a "keep both" rip in a fresh `(N)` sibling with tags intact) + the `_confirm_known_overwrite` dialog, all tested. (Full HW verification that the computed folder exactly matches cyanrip's on a marginal-title disc is still nice-to-have; the derivation mirrors the tested naming preview and can only *miss* a collision, never invent one.)
- **[x] Re-rip comparison + read-effort/reconciliation trust improvements — DONE (2026-07-09).** From a trust audit of a v0.4.23 re-rip that had *silently* regressed one track across rips (invisible because Platterpus is stateless per rip). New pure `rip_compare.py` diffs two `.platterpus.json` reports of the same disc (per-track byte-identity + better-master call) — surfaced via a `--compare` CLI, an off-GUI-thread results-pane banner after a rip (`find_prior_report` keyed on the new TOC-derived `musicbrainz_disc_id`/`cddb_id`, report **schema v9**), and a non-destructive `--assemble-best-of` CLI. Plus: a per-track **read-effort** warning (`heavy_reread` issue + footnote; complements — doesn't replace — the cross-rip diff, since a quietly-consistent-wrong read trips neither), an **AR↔CTDB reconciliation** line (`verdict.reconcile_ar_ctdb`), and **offset-variant explanations** (tooltip + User-Guide glossary). ~60 tests added; ruff + mypy clean. Fixed a recency-sort bug in `find_prior_report` (ISO vs `mtime:` string compare) in self-review.
- **[~] Finish the audit's un-run categories.** **Naming-scheme cross-FS safety — DONE (audited directly 2026-07-08):** no shippable bug on the Linux target; the NTFS/exFAT-reserved-name / length / collision hazards are a *documented cross-filesystem limitation* (now in `docs/dependency-contracts.md`), and re-sanitising cyanrip's output is rejected by Critical Rule #3 — the only open item is an *optional* non-blocking Settings warning (maintainer feature call). Input-validation — **now swept (confirmed 2026-07-09):** the Settings boundary (`settings_validation`) is comprehensive (completeness meta-test), AND the **config-file surface is validated at load** — `config.load()` calls `_sanitized()`, which runs the *same* `validate_config` boundary over the loaded TOML, logs every issue, and resets any error-level field to its default (so a hand-edited config.toml can't feed an out-of-range/`..`-traversal/control-char value into a rip). The **CLI-arg** diagnostic paths (`--doctor`/`--ctdb-calibrate`/`--compare`/`--assemble-best-of`) validate/handle bad paths in their own handlers (return exit codes, never crash). **Trust-claim-rendering sweep — DONE (2026-07-08):** two-phase verify+find-more workflow confirmed all 6 initial findings (one trust-critical) and found 5 more; **11 copy defects fixed** with regression tests (`tests/test_trust_copy_honesty.py`). The trust *engine* is sound; the dishonesty was static copy that drifted (an overclaim + stale "experimental" CTDB caveats from the KDD-16 flip). See `docs/archive/trust-audit-2026-07-08.md`. **The last remainder closed 2026-07-21:** the optional cross-FS Settings warning shipped (maintainer approved it) — `settings_validation.cross_fs_hazards` warns (never blocks) on a naming template whose *literal* text is Windows/NTFS-unsafe (reserved chars/device names, trailing dots/spaces); value-driven hazards stay a documented limitation (`docs/dependency-contracts.md` — the ripper owns naming, Critical rule #3). **Corrected 2026-07-31 — the "fully complete" claim above was wrong on three counts, all fixed in that session (see CHANGELOG):** (1) the config-file reset *was* logged but never **shown**, i.e. the silent reset the rule explicitly forbids, and for `read_offset` it silently ripped the next disc at the wrong offset (the hazard was already named in `main_window_drive._set_read_offset_override` and closed on the write path only) — every reset is now recorded and surfaced (GUI dialog + `--doctor`); (2) `--ctdb-calibrate` did **not** validate its path (a missing folder reported as "no FLACs found"; a relative `./-x` produced `-x/track.flac` argv entries that `flac` parses as options) — now validated and resolved at the boundary, `--compare`/`--assemble-best-of` really were fine; (3) the *value*-driven `.`/`..` hazard was filed as a cross-FS limitation, but it is a **path traversal on the Linux target** and ours to reject, not cyanrip's to map — the known-disc path fed `..` straight into `-D` (the unknown-album path had refused it since day one), now blocked by `settings_validation.path_segment_issue` at the track table and again in the argv builder.

### P1 — Documentation backlog

- **[x] Execute the 2026-07-21 docs-audit consolidation plan — COMPLETE 2026-07-21** (see [docs/archive/audit-2026-07-21.md](docs/archive/audit-2026-07-21.md) for the full findings + before→after map). The easy-tier fixes (~160 findings) were applied in the audit session; every captured restructure below is now executed (the parent box just lagged the last sub-item):
  - **[x] Rewrite the whipper-era test-plan cases — DONE 2026-07-21.** Test 3 rewritten as the wizard success-screens + auto-vs-manual offset capture (absorbing Test 4, retired); Test 8 rewritten as the cyanrip parity record + the still-open `-Z` convergence; Test 10 retired (feature inert under the sole backend; body in git history); A8 retired into A6; Part B is single-backend. Test numbers kept as stable IDs (retired numbers are one-line stubs). **New Tests 12–14** cover the owed hardware rows: read-speed ladder + auto-fix + speed-locked `-S` (Test 12), CD-Extra/data-track CTDB TOC (Test 13), EAC-compatible companion log + goal presets (Test 14).
  - **[x] Refresh the "⭐ Current plan & priorities (START HERE)" section above — DONE 2026-07-21.** The live queue now ranks what is actually open (trust hardening, soft-fork PRs, the hardware proof queue, this docs backlog, the UX remainder, parked CTDB repair); the 2026-06-09 numbered list is preserved verbatim-with-status as "ranked history" with its numbering intact, since other text cites "current-plan item N".
  - **[x] One canonical home for the UX gap backlog — DONE 2026-07-21.** `docs/ux-design-principles.md`'s ranked table is canonical (code comments cite its numbering); history item 15 above is now only a per-gap tracking checklist linking to it.
  - **[x] Slim CLAUDE.md's Companion-documents blurbs to one-line pointers — DONE 2026-07-21** (maintainer-approved; docs/README.md is the canonical annotated index, named as such in the list's preamble).
  - **[x] Archive the dated audits — DONE 2026-07-21** (both moved to `docs/archive/` with graduation rows; inbound links retargeted; the maintainer chose to archive the trust audit immediately rather than wait for the signing item — its open items stay tracked in the trust-hardening section above).
  - **[x] Move `docs/cyanrip-soft-fork-verify-meta-colon.c` → `scripts/cyanrip/verify-meta-colon.c` — DONE 2026-07-21** (kit README Files row added; runbook, test docstring, index, and PLANNING tree references updated).
  - **[x] Finish the cyanrip-cluster dedup — DONE 2026-07-21** (runbook blockquotes → links to the canonical kit paste files; upstream-process facts consolidated into the roadmap's Process block, strategy §6 + runbook link there).
  - **[x] Single-home cleanups — DONE 2026-07-21.** README's second EAC-parity telling folded into the top matrix (audit session); `docs/eac-parity.md`'s restatement of the two-artifacts rationale trimmed to a pointer (architecture §3.7 owns it); `tests/fixtures/README.md`'s baseline section reduced to a pointer at `output_reference/` + the UTF-16/`decode_log_bytes` warning; `docs/dependency-contracts.md` gained an explicit scope note naming what it deliberately excludes (installer/desktop-integration/GitHub-API surfaces → `deps/`, `appimage_integration.py`, `update_check.py`); `docs/architecture.md` §2's layer table gained a "Qt-free domain modules" row pointing at PLANNING §2 as the canonical per-module map.
  - **[x] Write the manual CUETools/`ctdb-cli` repair workflow — DONE 2026-07-21:** [docs/manual-ctdb-repair.md](docs/manual-ctdb-repair.md) (linked from both recommending docs + the index). Assembled strictly from the existing research record; every step we haven't executed on project hardware is marked *(unverified)*. In-app repair stays parked (KDD-14 Phase 2).
  - **[x] Condense the "two corrections to the ripper-landscape doc" — DONE 2026-07-21 (both halves):** PLANNING.md KDD-24 keeps the full text (the designated record); the feasibility doc carries a one-line summary + link. The strategy §9 citation is resolved: the maintainer didn't recall the doc's location, and a repo-wide search confirmed it was **session-provided research input never committed to the repo** — §9 now records that, points at where its claims are preserved/corrected (the parity scorecard, §9's notes, KDD-24), and names the save-to-`docs/archive/`-if-it-resurfaces convention.
  - **[x] DEPENDENCIES.md review-cadence catch-up — DONE 2026-07-21** (shipped in the audit session/PR #84 itself; this checkbox just never got flipped): the maintainer chose the catch-up over relaxing the cadence, and the dated 2026-07-21 review covering v0.4.19–v0.4.24 is logged in `DEPENDENCIES.md`'s retirement-review log (all pins healthy; the `build>=1,<2` bound applied the same day; mypy's `<3` bound noted as load-bearing).

Items that need real-system output to write authoritatively. Address as T32's smoke test on a real Bazzite system surfaces the actual output. Each is small (a paragraph or two of README) but writing them now would be guesswork.

- **[x] Verify Step 5 end-to-end with a real CD — RE-SCOPED & folded (2026-07-21).** The original whipper premise is dead (`whipper drive analyze`/`offset find`; whipper gone, KDD-18; cyanrip has no offset finder — the offset comes from the bundled AccurateRip list or manual entry in the wizard). The test-plan rewrite this row was waiting on (Tests 3–4) already landed in the 2026-07-21 docs audit, so nothing doc-side remains open here: the only surviving work is the real-hardware *wizard-flow* confirmation, which now lives once in the **hardware-gated proof queue** (START-HERE item 3 / test-plan Tests 3–4). Closed as a standalone row to avoid double-tracking.
- **[x] "You should see X" success indicators for the drive-setup flow — RE-SCOPED & folded (2026-07-21).** Same disposition: the whipper-CLI premise is gone, the drive-setup copy was rewritten in the docs audit, and any "what success looks like" screens must be captured on a real-hardware wizard run — tracked once in the **hardware-gated proof queue** (Tests 3–4), not as its own open row.
- **[x] Drop the "Method C is the only working path right now" blockquote — done.** The README now leads with Method A (AppImage, a published release asset) as the recommended path; Method B (PyPI via the new publish workflow) and Method C (source) follow. No "only working path" caveat remains.
- **[x] Remove the Method C "private repo, authenticate first" blockquote — done.** The repo is public; the README's auth section states a plain HTTPS `git clone` needs no authentication (auth only matters if you intend to *push*).
- **[x] Add a Quick Start for users who already have whipper + Distrobox set up — done 2026-06-02.** README quickstart now has an "Already have whipper + Distrobox set up?" callout pointing at `install.sh --no-host` (GUI-only), for re-installs or a second box sharing the stack.
- **[ ] Add a screenshot or two** of the GUI to the top of the README once T32 confirms it looks right on Bazzite KDE Plasma 6. *(Needs a real GUI screenshot — hardware/display; [docs/test-plan.md](docs/test-plan.md) Test 5.)*
- **[ ] Document Picard's actual auto-launch behavior** under Step 6 once T32 verifies it. The README currently says it works "if you enable the toggle"; T32 will confirm what the toggle UX actually feels like end-to-end. *([docs/test-plan.md](docs/test-plan.md) Test 6.)*
- **[x] Sanity-check the "Where things live" table — done 2026-06-02.** Added a row for the rip output folder (`Artist/Album/`) documenting that whipper writes the FLAC tracks **plus** `.log`/`.cue`/`.m3u`/`.toc` next to them — confirmed on the real 16-track T32 rip (KDD-13 findings). Output goes under the configured output dir (not the working dir).

### P1/P2 — Upstream open-source modification for EAC parity (investigation 2026-06-02)

Previously it was out of scope to modify the programs underneath us; this is the first pass at "what would modifying open-source upstream buy us toward full EAC parity?" Full write-up, with reasoning and sources, in **[docs/archive/upstream-modification-investigation.md](docs/archive/upstream-modification-investigation.md)**. Headline: most of EAC's *correctness* is already delivered by whipper, so the wins are additive tools (CTDB), not whipper changes. **Guardrail:** prefer wrapping a separate maintained tool → upstream PR → (last resort) a maintained fork. Do **not** fork whipper (unmaintained; successor is `cyanrip`).

**Feasible (prioritised — priority shown in bold, status with the usual marker):**
- **[x] CTDB verify (read-only)** — **HIGH. DONE** (library 2026-06-03, clean-room per KDD-16; GUI-wired 2026-06-17; **CRC hardware-validated 2026-07-07**). Protocol/CRC spec preserved in [docs/archive/upstream-modification-investigation.md](docs/archive/upstream-modification-investigation.md); status is canonical in **current-plan item 8**.
- **[ ] CTDB parity repair** — **HIGH; shipping DECIDED "D → B" (maintainer 2026-07-21), demand-gated.** KDD-14 Phase 2; the one genuine "beyond EAC" everyday win. Wrap `ctdb-cli verify|repair`; depends on verify. `ctdb-cli` is C#/.NET 10 (correction 2026-06-02), so the ship decision is: **D** manual workflow now ([docs/manual-ctdb-repair.md](docs/manual-ctdb-repair.md)), **B** optional dep-subsystem tool when a real user hits it — **not** an AppImage .NET bundle. See KDD-14 and the investigation doc.
- **[x] Upstream whipper bug fixes — CLOSED, no upstream to route to (2026-07-21).** `whipper cd info` non-zero exit on unknown discs and HTOA accuracy edge cases (issues #75/#82) were about *whipper* upstream specifically; whipper was fully removed as a backend 2026-06-30 (KDD-18), so there is no longer an upstream we're routing fixes to. Closed rather than left dangling: the cyanrip soft-fork below is the live upstream-contribution path now, and HTOA stays out of scope regardless of backend (see the explicit HTOA note under "Out of scope" below).
- **[x] EAC-style signed log checksum — CLOSED, superseded by research (2026-07).** Re-evaluated as part of the tracker-log-acceptance research session: this item proposed literally the forgery this project's own rules reject (CLAUDE.md Critical Rule #8's spirit + the brief's "never fake a log/checksum") — signing a log as if EAC produced it. **Decision: do not build this.** The tracker-acceptance path it was aimed at is out of scope *by design*, not by degrees — see PLANNING.md **KDD-24** and `docs/eac-parity.md`. The follow-through work that actually matters for trust is already tracked separately: **CTDB CRC hardware validation** (KDD-16's remaining step — pinning the bit-exact CRC trim against a real CD and flipping `crc.CRC_VALIDATED`; see the "⭐ EAC output-parity proof matrix" section and `docs/test-plan.md` Test 1), not a signed checksum.

**cyanrip upstream contributions — via a SOFT FORK (decided 2026-07-08).** cyanrip is the sole backend (KDD-18), LGPL-2.1, Meson+ninja, GitHub issues/PRs; **releases stalled (last tag Jun 2024) but `master` live** (commits to Mar 2026 — see `cyanrip-fork.md` Part A §6). Decision: maintain a **soft fork** `rmccann-hub/cyanrip` = upstream `master` + a small rebased patch set, **PR each patch back upstream** and drop it from the fork once merged — a staging area + fallback, never a divergence. **Full runbook, verbatim bug analysis, minimal patches, and ready-to-paste issue text: [`docs/cyanrip-fork.md`](docs/cyanrip-fork.md).** Rules: their C conventions win; one focused change per PR; build from our commit in the `ripping` container so we don't wait on a cyanrip release. *(Execution is env-gated: the Platterpus cloud session is scoped to `rmccann-hub/platterpus`, so fork/build/issue happen locally or in a cyanrip-seeded session.)*
- **[~] ⭐ Colon-in-tag-value parsing fix — PREPARED (patch + issue drafted in the runbook).** Confirmed in `master`: `append_missing_keys` (`src/cyanrip_main.c`) tokenises `-a`/`-t` with `av_strtok(src, ":")` (no `=`/backslash awareness) *before* `av_dict_parse_string`, so a literal `:` in a value gets a spurious key injected — the bug behind our `_escape_meta_value` U+2236 substitution + `restore_substituted_colons` metaflac pass. **Fix (minimal, in the runbook):** skip the positional-key injection when the string is already explicit `key=value` (an `=` before the first `:`); callers then pass `\:`, which `av_dict_parse_string` unescapes. **Payoff:** delete the colon-substitution + metaflac-restore workaround (behind a version guard, only after the fixed cyanrip is live in the container).
- **[~] Full FLAC (libavcodec) encoder arguments — PREPARED (design + issue drafted in the runbook; maintainer-requested 2026-07-08).** cyanrip hardcodes `avctx->compression_level = cfmt->compression_level` and opens the encoder with `avcodec_open2(…, NULL)` (`src/cyanrip_encode.c`), so FLAC compression (and every other encoder option) can't be changed. **Design:** a repeatable `-O key=value` that builds an `AVDictionary` passed to `avcodec_open2` — generic across codecs, defaults unchanged, gives full FLAC control (`compression_level`, `lpc_type`, …). **Payoff for us:** a validated Settings knob for FLAC level/args, FLAC-as-max still the default.
- **[ ] Structured/JSON output mode (`--json` or similar) — RUNNER-UP.** cyanrip's finish log is human-readable and we regex-parse it (`parsers/cyanrip_log.py`, "never-raise" + golden-tested because the format can drift). A machine-readable output would make every GUI's integration robust. Bigger; design as *additional* output, never replacing the log.
- **[ ] In-encoder FLAC decode-verify option — LOW (already worked around).** cyanrip could gain a `--verify` decode-check after encoding; we already cover it post-rip (`adapters/flac_verify.py`, `flac --test`), so it's a nicety, not a need.
- *Note:* cyanrip's overread (`-O` — **not** `-x`, which doesn't exist; corrected 2026-07-21) and pre-emphasis flags already exist upstream — using them is a **Platterpus-side** call, not a cyanrip change. The overread toggle shipped 2026-07-21 (EAC parity-gaps section); de-emphasis stays deliberately unused (flag-only preservation, `docs/dependency-contracts.md`).

**Non-feasible / not worth it — do NOT revisit without a rethink** (full rationale in the doc):
- **AccurateRip submission** — permanently blocked by operator policy (EAC/dBpoweramp only). Not a code problem. *Verification stays in scope and works.*
- **CTDB submission** — almost certainly the same trust-gate; shelved.
- **C2 error-pointer reading** — would require deep C-level surgery on `libcdio`/`cd-paranoia` for marginal gain (whipper is already bit-perfect via overlap + AccurateRip). Treat as build-from-scratch.
- **Literal two-full-disc-pass Test&Copy** — whipper already does per-track test+copy CRC; the whole-disc double pass adds marginal assurance at 2× time.
- **Byte-for-byte EAC log format parity** — moving, semi-proprietary target; not worth it beyond the optional checksum above.
- **Separate drive-offset/feature database** — redundant with AccurateRip's offset list (already used).
- **In-house from-scratch ripper** — out of scope; the breakage path is migrate the adapter to `cyanrip`, not rewrite.

### P1 — Install ergonomics follow-ups (2026-06-02)

- **[x] Add openSUSE / Tumbleweed (`zypper`) support to `setup-host.sh`. Done 2026-06-02.** Added `*suse*) zypper --non-interactive install …` branches to both `ensure_distrobox` and `ensure_container_backend`, so openSUSE now auto-installs Distrobox + podman (README table upgraded from ⚠️ Partial to ✅ Fully). Also made distro detection testable via an `OS_RELEASE_FILE` override; new behavioural + static smoke tests in `tests/test_setup_host_script.py`.

### ⭐ P1 — Release plan: v0.6.4 (non-beta) — PLANNED, NOT CUT

> *"Get ready for a new non-beta release, but just plan for the release for now."*
> — maintainer, 2026-08-04

**Status: BLOCKED, and the blocker is the gate working correctly.**

```
$ python3 scripts/handshake.py --release-gate            → exit 1  (refused)
$ python3 scripts/handshake.py --release-gate --prerelease → exit 0  (permitted)
```

Round 7 is OPEN and **both** sides declare HOLD. Per the deviation policy, releasing
or moving the pin while a round is open is a *must-ask* — and per `CLAUDE.md` rule 12
the gate is bilateral, so this is not a formality to wave through. **A `v0.6.4`
stable tag must not be dispatched until round 7 closes with GO on both sides.** A
further beta (`v0.6.4b4`) is permitted at any time and needs none of this.

What the release itself is waiting on is therefore **not** code — the work below is
either done or mechanical — it is the rig session (see the round-7 section) and the
two verdicts turning GO.

#### The blockers, in the order they must clear

1. **[ ] The rig session: H9, H10, H12, T9, T12, T13.** Capture **stdout for every
      invocation**; artifacts to both repositories. This is the round's remaining
      evidence and nothing else can substitute for it. Hardware-gated.
   - **Ordered sheet for this exact pair: [`docs/archive/rig-session-c5fb909.md`](docs/archive/rig-session-c5fb909.md) (superseded by [`docs/rig-session.md`](docs/rig-session.md))**
      — `v0.6.4b4` + `c5fb909`, six steps cheapest-first, with the pre-flight checks and
      the fill-in blocks. Written 2026-08-04 at the maintainer's request instead of them
      working from the 40-case checklist; `hardware-test-checklist.md` stays the full
      reference and the sheet points into its §F1/§F2/§F3.
   - **It opens with a correction worth carrying here too:** `-O` (force overread — our
      Settings toggle, and what H10/F2 is about) and `-x` (the fork's **cache probe**,
      which our 16-flag argv surface does **not** contain) have both been called `-x` in
      this correspondence. `cyanrip_backend.py` records that the `-x` older project notes
      named *"does not exist in cyanrip's getopt at all, so passing it would abort every
      rip."* Their lap-21 §H ask for `-x` means their probe, run directly against the
      binary — not something Platterpus can invoke.
2. **[ ] The fork's reply to lap 25** — the round is one exchange from closing:
   - **[x] The rig session ran** (2026-08-04, `c5fb909`): 14/14 vs EAC, log verification
      `verified`, first hardware sightings of `Read stalls:` and `C2 errors: unsupported by
      drive`. `HANDSHAKE-TESTED` declared in lap 23. Record:
      `docs/handshake/artifacts-round-07/rig-session-results-c5fb909.md`.
   - **[x] Their lap 24 answered the pin question**: promote **`e61e75a`** rather than
      `c5fb909`, because `c5fb909` carries a `dev_path` leak that had made their sanitizers
      unusable — and `e61e75a` is **observably identical** to it (log body 275 lines, cue,
      decoded PCM, `-j` record, measured side by side), so the rig evidence transfers.
      Accepted; test pin moved.
   - **[x] The go-first deadlock was OURS, not the shared spec's.** Their lap 24 §B1 tested
      their loader against our exact case and it accepts a first GO while correctly refusing
      to close. Our gate was always right; only `check_wire_header` conflated *well-formed*
      with *closable*. Fixed narrowly — see the CHANGELOG.
   - **[x] `v0.6.4b5` cut against `e61e75a`** (their §E1), and the session procedure rewritten
      as three human steps plus `scripts/rig_session.sh` (their §E2).
   - **[ ] The second rig session** — `docs/rig-session-e61e75a.md`. The remaining evidence
      is `-x` on a real drive (never executed anywhere, ever), `-j` from a physical drive, a
      deliberate abort, and a mid-rip cancel. **No parity re-run needed.**
   - **[ ] Then both GO on `0.9.4-rc1+platterpus.5`** cut from `e61e75a`, we move `FORK_PIN`,
      and stable `v0.6.4` dispatches.
   - **[ ] Round 8, one bump, four agreements now**: the naming convention, the ordering
      rules with lap 22 §B1/§B2's qualifications, `Handshake-Round`/`-State`/`-Release`/
      `-Lap`, **and the §5 first-GO clarification** (their §B2 preferred it over a `READY`
      token, because a new verdict word would meet older gates that correctly treat an
      unrecognised verdict as *not agreement*).
   - **[ ] Still not received: the P1 flag table.** Their lap 24 §F says
      `PROVIDER-CONTRACT.md @ e61e75a` shipped with the lap; **it did not arrive** — four
      files came (audit, beta note, golden reference, lap). So our argv check is still
      diffing against round 6b's table, ratcheted as `_MAX_TABLE_LAG`.
   - **[x] Their golden reference from `e61e75a` arrived** and re-parses clean — and it
      carries `Pregap source: TOC` on tracks 1 and 2 (150 and 75 frames), which is the C1
      case we had recorded as having no available test.

3. **[ ] Superseded: the fork's reply to lap 22** (`verified/round-07-lap-22.md`) — two files
      and two record corrections, none of them blocking:
   - **[ ] The golden reference from `c5fb909`** (§C3a). Their lap 21 §E says it exists
      and was committed with the lap file in *their* tree; it has not reached this
      repository. Every previous one did, and per-line re-parsing is where lap 13 found
      the pre-gap double-count they then fixed. Name it
      `round-07-lap-22-golden-reference-gc5fb909.log`.
   - **[ ] The P1 flag table back inside a lap file, or `PROVIDER-CONTRACT.md` as a lap
      artifact** (§C3b). **Not a preference.** None of round 7's twenty-one laps embeds a
      flag table — every one points at a file in their repository — so the newest table we
      hold is round 6b's, from before this round opened, while their lap 21 reports the
      count moving 40 → 41. This is the `-V` situation with one extra step: then the
      evidence was in a committed file undiffed; now the file is not here at all.
      Ratcheted as `_MAX_TABLE_LAG` in `tests/test_argv_surface_agreement.py`.
   - **[ ] Confirm the four-commit `beta.1` span and whether the counter now moves with
      the anchor** (§D1/I2). `cyanrip 0.9.4-rc1+platterpus.5-beta.1` is declared by laps
      8–20 across `9003e6f`, `ceca8bc`, `f00cb2b` and `486dce3`, with the source anchor
      moving **twice** underneath it — and one of the changes it spans is a log value we
      parse. Also §D2: laps 12 and 14 name a build in `HANDSHAKE-RIPPER-VERSION` that
      their own delivered artifact's banner contradicts.
   - **[ ] Round 8, jointly: one shared-spec bump, THREE agreements — and rules 1 and 2
      are corrections, not additions.** `handshake-protocol.md` §3 has carried *"absent
      means lap 1"* and *"never by filename or mtime"* since the file was created
      (`fec0ca3`); both implementations violated both for its whole life, because **§8 has
      no conformance row for either** (lap 22 §I1 asks for three). The bump carries the
      naming convention, the ordering rules **with lap 22's two qualifications** (§B1: the
      pre-v2 name fallback must be stated; §B2: a header-bearing file with no lap field is
      not the "pre-lap-header file" the rule is about, and fails closed instead), and
      `Handshake-Round`/`-State`/`-Release`/`-Lap`. That file is shared and **neither
      project owns it**, so it stays untouched while a round is open.
   - **[x] Test pin moved to `c5fb909`** (`0.9.4-rc1+platterpus.5-beta.2`), `9003e6f`
      retired into `SUPERSEDED_TEST_PINS` rather than deleted — it held for thirteen laps
      and is what the 2026-08-04 rig ran, so a rig that has not rebuilt still gets
      `--consumer`. Production pin unmoved: round 7 is open.
   - **[x] Their lap-20 §I1 ordering diff, run rather than agreed** — two divergences,
      both ours, both against the spec rather than against their wording; plus the gate
      now refusing the two states ordering can only hide. Lap 22 §B.
   - **[x] Their I1 (`-j` is a no-op) confirmed by running it**, and confirming it found
      the argv-surface check reading round 6's table since the rename. Lap 22 §C.
   - **[x] Lap 17's §C adopted by the fork** as specified — no counter-proposal, no
      sender in the name, padding kept. Their lap 18 also reported their loader's
      ordering, which is what exposed our two divergences.
3. **[ ] Superseded: The fork's reply to lap 17** (`verified/round-07-lap-17.md`) — their answer
      on the **file naming convention** (§C: adopt `round-NN-lap-LL.md` for their
      outbound files, add the check, or propose a different shape — one convention beats
      the better convention), and whether they put the **stock version-flag matrix** in
      their contract as a stated-not-derived section (their J1; we said yes and why).
   - **[ ] Round 8, jointly: one shared-spec bump, two agreements.** The
      machine-readable handshake state (`Handshake-Round`/`-State`/`-Release`/`-Lap`)
      **and** the naming convention as a section of `docs/handshake-protocol.md`. That
      file is shared and **neither project owns it**, so it is deliberately not edited
      while a round is open.
   - **[x] Lap 15's D1–D3 answered** in their lap 16: they built stock 0.9.3 and
      measured — `--version` does **not** exist there, so the probe order stands and
      their lap-14 advice is withdrawn. `-Y`'s stock range is terminal-unknown. Both
      commits are now named for each golden reference.
3. **[ ] Superseded: The fork's reply to lap 15** (`verified/round-07-lap-15.md`) — **D1** does stock
      cyanrip 0.9.3 accept `--version`? That is the *only* thing blocking the version-
      probe reorder they asked for (their J3), and it is a claim in **our** own table
      that we cannot check: row 1 says 0.9.3 takes `-V` and not `--version`, from
      reading upstream's source rather than running a 0.9.3 binary. If they confirm
      0.9.3 *does* accept it, reorder to `("--version", "-V")` immediately — no
      population pays. **D2** name both commits for the golden reference (its banner
      has never matched the commit their lap names it by; benign, but rule 12's third
      instance). **D3** closed — there is no clean "since X" for stock `-Y`, so `None`
      for stock is terminal, not a gap they owe us.
   - **[x] Lap 13's D1–D4 all answered** in their lap 14: the pregap bug fixed (`150`
      authoritative), the four `Read stalls:` shapes published, `-Y` traced to upstream
      `443f749`, and the `-V` range table given.
3. **[ ] Superseded: the fork's reply to lap 13** (`verified/round-07-lap-13.md`) — **D1** a golden
      reference with a *populated* `Read stalls:` line (we parse the value as text
      because `none (…)` is the only shape we have seen); **D2** the earliest build
      with `-Y`, which is what restores a reachable `failed` verdict for stock
      cyanrip; **D3** which of track 1's two pre-gap values is authoritative (§C —
      300 vs 150, two internally-consistent pairs, track 2 the control); **D4** the
      range on the `-V` special-casing, which sits outside `--help` and so cannot be
      derived by our argv-surface test. Their lap 12 answered everything else.
   - **[ ] Round 8: the machine-readable handshake state**, agreed both ways —
      `Handshake-Round` / `Handshake-State` / `Handshake-Release` / `Handshake-Lap`.
      Deliberately not inside round 7.
3. **[ ] Superseded: the fork's reply to lap 11** (`verified/round-07-lap-11.md`) — D1 confirmation, D2
      (their own §4 question, our view given), D3 (contract ranges), and their answer
      on the **J1 machine-readable test-pin shape** we proposed. Their lap 10
      (`verified/round-07-lap-10.md` is *ours*; theirs was the inbound file) raised H1–H6 and
      J1–J6; **all six findings are fixed** and every J is answered in lap 11.
3. **[x] Q8 — answered, and the addendum fix is landed anyway.** Their lap 10
      confirmed the `-Z N -l <tracks>` pass *does* write a complete, valid,
      self-checksummed cyanrip log. We took **route 1 (the sidecar)** rather than
      route 2 (cite that log) because route 1 needed no round while one is open —
      route 2 remains the better *record* and is filed below as its own change.
4. **[ ] Route 2: cite the re-rip's own log instead of paraphrasing it.** The better
      record, deliberately **not** batched with the H1 fix: it changes which files an
      album folder contains, which is a contract of ours with users and with tooling
      we do not control. Same reasoning that made us keep `-j`'s explicit path.
5. **[ ] `-x` on one throwaway rip** (their J6). The least-tested path in the binary,
      never measured on hardware; the fork's new stall report makes the cost one track
      rather than a session. First group of the hardware plan, not the last.
6. **[ ] Both verdicts GO.** One side's GO against the other's HOLD is an open round;
      the gate reads both and will keep refusing until it is not.

#### The release ritual once it is unblocked (mechanics: `CLAUDE.md` → CI/release)

Nothing here is novel — it is the standing checklist, written out so the cycle is not
reconstructed from memory under time pressure:

1. **[ ] Bump `src/platterpus/__init__.py` `__version__` → `0.6.4`.** The single
      source; `pyproject.toml` reads it dynamically. Do **not** add a version there.
2. **[ ] Move the `[Unreleased]` entries** under `## [0.6.4] — <date>` with a matching
      compare link, and point the `[Unreleased]` link at the new tag.
3. **[ ] `pytest tests/test_no_stale_version_claims.py`** — the version-bump gate. It
      fails until the CHANGELOG has both a section *and* a compare link, `[Unreleased]`
      points at it, and README/SECURITY name the new minor with its stamp. This exists
      because the README once announced v0.5.x deep into the v0.6 line: a doc-stamp
      records *when a doc was edited*, and a doc nobody edits keeps an accurate stamp
      while its prose quietly expires. **Two different things, two different checks.**
4. **[ ] `pytest tests/test_doc_version_stamps.py`** — restamp every Markdown doc the
      cycle touched. As of this writing that is `PLANNING.md`, `TASKS.md`,
      `docs/README.md`, the error-reporting design of record (now `docs/architecture.md` §3.7a) and the round-7 files, all already at
      `v0.6.4b3` and therefore all needing one more move.
5. **[ ] `python3 scripts/emit_dependency_contract.py`** — the generated consumer
      contract now names the app version in its §0, so a version bump *changes it*.
      This is deliberate (it states the range its claims cover) and the regeneration is
      part of the bump, not an afterthought. `--check` is the CI gate.
6. **[ ] `python3 scripts/handshake.py --release-gate`** — must exit 0. If it does not,
      **stop**; that is the whole point of it.
7. **[ ] Full green run** — `pytest` on the matrix, `ruff check` + `ruff format
      --check`, `mypy`, the changelog check, media-guard, `pip-audit`.
8. **[ ] Dispatch `release.yml` via `workflow_dispatch` with `v0.6.4` as the input.**
      It creates the tag itself; a tag push does not work from the cloud session and
      the agent git proxy forbids it anyway.
9. **[ ] Confirm the artifacts**: AppImage + `.sha256` + `.zsync`, the signed
      build-provenance attestation, and the PyPI wheel+sdist from the dispatched
      `publish-pypi.yml`. A `v0.6.*` tag publishes as a **pre-release**; `v0.6.4` is
      *not* a `v0.*`-style pre-release by tag shape, so verify the release is marked
      correctly rather than assuming.

#### What this release will contain

The error-reporting work above, in full, plus the three betas' fixes: the AppImage
built from PyPI instead of the tree (b1), the diagnostics that made the fork-build
failure visible (b2), and the unexpanded `$HOME` that b2's diagnostics revealed (b3).
The CHANGELOG `[Unreleased]` section is the authoritative list.

#### Two things deliberately NOT in it

- **`--consumer platterpus/<version>` on every rip.** An argv change, and the argv
      chokepoint is validated — it lands with its own range check and test, not
      batched with a release.
- **Moving the pin to any round-7 test build.** The pin is `2f950c8` and stays there
      until a round closes on a successor.

### ⭐ P1 — Full error reporting & diagnosability (maintainer directive, 2026-08-04)

> *"do a full check for error reporting to both Cyanrip and Platterpus, as many and as
> full surface coverage as possible, even if you think it's not needed. I want full error
> and reporting to the output log file (JSON) as possible for future debugging. Be
> thorough and verbose; make finding errors easy."*

Four parallel read-only audits (subprocess capture, swallowed exceptions, the JSON report
surface, and user-facing surfacing) produced a ranked list. The recurring shape is **not**
"we never obtained the fact" — it is *"we had the fact and discarded it"*, which CLAUDE.md
calls the worse of the two, because the report still looks complete either way.

- **[x] One collector — `diagnostics.py` + the report's `diagnostics` block (schema v16).**
      One `record()` writes to the text log **and** the JSON, so the two artifacts cannot
      describe the same event differently. Greppable `platterpus-diagnostic` prefix; the
      block states its own scope, its truncation and its count.
- **[x] Eight new `issues[]` checks.** Each was a fact that could be true while the one
      list a triager opens first said "nothing to flag" — most sharply `recompress_failed`
      (the step that rewrites archival masters was not a parameter of the deriver) and the
      whole v15 handshake-approval block, which was read by nothing at all.
- **[x] `adapters/tool_run.py` — a channel for the tool's own words.** The three post-rip
      adapters declared their command seam as `Callable[[list[str]], int]`, which made it
      *structurally impossible* for a dependency's output to reach the result, the report
      or the user. Adds a third state (`started`) so a missing binary and a wedged file
      stop being the same value.
- **[x] `metaflac` — the worst single gap.** Runs on every rip; captured nothing.
- **[x] `cd-paranoia -A`'s exit code, `eject`'s message, the `except OSError: pass` that
      could send a rip into the folder the user was avoiding, and the drive-offset CSV's
      unlogged row skips.**
- **[x] The minimal failure report must carry `captured_stdout` + `debug_log`.** Ranked #1
      by the surfacing audit: on exactly the rips the minimal report exists for, the
      ripper's whole output reaches neither screen, nor `log.txt` (INFO by default), nor
      the one artifact written — while sitting in a variable the code already knows how to
      serialise.
- **[x] Stop `"Rip failed."` clobbering the captured error text.** `_finish_rip` reads only
      `worker.failure_hint`, never `_last_rip_error`, so on every start/stream failure the
      specific sentence is replaced by the generic one two lines after being stored.
- **[x] Failure surfaces must name the log path, XDG-aware, and never no-op silently.**
      ~20 dialogs say "see the log" with no path; two hardcode `~/.local/share/...` against
      an XDG-aware `paths.py`; a crashed dependency probe makes *Tools → Check
      dependencies* do nothing visible at all.
- **[x] Close `report_types.py` drift and make its test a sweep**, not three anchored blocks.
- **[x] A copyable diagnostics surface.** There is no export, bundle or copy action
      anywhere in the UI, and the one place a cyanrip fatal is displayed cannot be selected.
- **[x] Failure paths must log at ≥ WARNING.** `log.txt` is INFO-only by default, so every
      DEBUG subprocess record — including cyanrip's entire transcript — is absent from a
      bug report unless the user had already turned Debug logging on.
- **[x] Carry it into the next handshake lap**, so both projects hold the same
      expectations for what each side captures, surfaces and can be asked for. Sent as
      lap 10 (`verified/round-07-lap-10.md`, **HOLD** — the round stays open). It states our
      half so they can hold us to it, and asks three things back: confirm the same
      promise on their side; answer their own lap-7 §4 on the seven stdout-only refusal
      paths (**our view: document them as stdout-only rather than opening the logfile
      earlier — a logfile opened before the disc is validated trades an old ambiguity
      for a new one**); and state the *range* a contract claim covers rather than the
      snapshot. We owed the third one too, so the generated consumer contract now opens
      with a §0 naming exactly which app version and which approved ripper build its
      claims cover.

### ⭐ P1 — EAC parity: **CLOSED at 14/14 on real hardware (2026-08-04)**

The rig rip of the baseline disc — b3 + `platterpus-fork-g9003e6f`, same drive, offset
+667 — is **bit-identical to EAC on all 14 tracks**, and its ten `Pre-gap length` rows
match EAC's to the hundredth of a second in order. Artifacts committed to
`output_reference/cyanrip_fork_flac/`; proven by `tests/test_fork_rip_eac_parity.py`,
which reads them.

- **[x] EAC output-parity proof matrix — FLAC, 14/14.** Track 5 reached parity only via
      the auto-fix re-rip (first pass `6902BCF0`, shipped `E0036697` = EAC's), so the
      artifact is also the proof that feature works on hardware.
- **[x] KDD-32 / `INDEX 00` pre-gap shortfall — closed for the fork.** Stock 0.9.3 still
      reports "None signalled"; both branches stay in `_gap_handling`, whose docstring
      was corrected (it still described the shortfall as open).
- **[ ] MP3 / WAV parity rows** — the matrix's other formats are unchanged and still
      pending; only FLAC is proven.

### P1 — Open from cyanrip handshake round 7 (2026-08-04, OPEN — lap 10 sent, both betas cut)

Four files so far: our `outbound/round-7.md`, their `inbound/round-7.md` (lap 1), our
`verified/round-7.md` (lap 2), their `inbound/round-07-lap-02.md` (their lap 2), and our
`verified/round-07-lap-03.md` (lap 3). **Both sides declare HOLD.** The round is OPEN and
**neither project releases** — now enforced bilaterally rather than remembered.

The pin stays `2f950c8` (r2). **Four SHAs in one open round** — `ad65a24` → `d5d12ec`
→ `345241b` → `5bc654d` (r4, `0.9.4-rc1+platterpus.4`) — recorded as
`NEXT_PIN_UNDER_REVIEW`, **not installed**. The gate is what has kept us on r2
through all four.

**Protocol v2 adopted.** `docs/handshake-protocol.md` is the SHARED spec, verbatim
from the fork; our own §8 points at it instead of restating it. Conformance is
`tests/test_handshake_conformance.py`, one test per §8 row (T15 — **done**, and it
found row 12 failing on our side: an empty record allowed a release).

**We had not sent them `outbound/round-7.md`.** They asked three times; Q8, which we
cited three times as blocking our addendum fix, was in it. Delivered with lap 3. Our
process failure, not their oversight: the protocol says two files per round and we sent
one.

**The deadlock, and the two betas.** The fork found that our shared rules are
unsatisfiable as written (their lap 6 §1): a round cannot close without
`HANDSHAKE-TESTED`; that evidence needs the reviewed build on the rig; installing it
is forbidden while the round is open. Their fix is `HANDSHAKE-TEST-PIN` — a build for
gathering evidence, which never closes a round and never moves the production pin.
Adopted. Ours is a **pre-release**, because our artifact is an AppImage a user
downloads rather than a tree they build: `--release-gate --prerelease` permits it
loudly, `--release-gate` still refuses a stable release.

**Both betas are cut and both are named in writing (their lap 8, our lap 9).**

```
Platterpus  v0.6.4b1                        GitHub pre-release, assets attached
cyanrip     0.9.4-rc1+platterpus.5-beta.2   commit c5fb909 on platterpus-fork
                                            (was beta.1 / 9003e6f — moved in lap 21)
```

**`beta.1` was worn by four commits, which is why the *tag* is the pin and the version
never is.** Laps 8–20 all declare `0.9.4-rc1+platterpus.5-beta.1`, across `9003e6f`,
`ceca8bc`, `f00cb2b` and `486dce3`, while `HANDSHAKE-SOURCE-ANCHOR` moved twice
underneath it — and one of the changes it spans is a **log value we parse** (track 1's
`Pregap length:`, the lead-in counted twice). Our classifiers key on the build tag, so
nothing here broke; a human reading a report's `ripper_version` could not have told which
behaviour they had. Raised as lap 22 §D1/I2.

- **[x] Platterpus test pin: `v0.6.4b4`** — published pre-release, superseding `b1`.
      Cut when the fork moved their test pin to `c5fb909`, and **the reason is the delivery
      vehicle, not symmetry**: the wizard and `--install-ripper` read `WIZARD_TARGET`, a
      constant that ships *inside* a release, so a user on `b3` had no in-app route to
      `c5fb909` — and a hand-built `c5fb909` would have had `--consumer` **withheld**
      (`accepts_consumer_flag` → `False`, a silent `Consumer: not identified` in the rig
      log) and log verification reported `not_determined`. Measured on `b3`, not assumed.
- **[ ] Wire `observed_version_pair_line()` or delete it.** Exported, tested, and called
      from **nowhere** in `src/` — the `RipHandle.cancel` shape. Nothing is missing from a
      diagnosis (the report carries `ripper_version` / `ripper_build` /
      `ripper_handshake_approval` structurally); what is missing is the *rendering*, and
      its docstring asserted a use it does not have. The docstring now says so rather than
      a call site being invented during a release.
- **[x] Adopt the fork's beta as the wizard's build target.** `WIZARD_TARGET` →
      `9003e6f`, checked out as an exact detached commit; `platterpus-fork-g9003e6f`
      added to the `--consumer` allowlist so rig logs carry both halves of the pair.
      **The test pin moved twice inside this round** (`f750890` → `d9c7124` →
      `9003e6f`), each move retiring a build the previous lap named — `f750890` because
      its `-x` could hang with no diagnostic at all, which is exactly what H10 exercises.
      `SUPERSEDED_TEST_PINS` records the retired ones, and a rip that finds one installed
      says it is retired and names the current one.
- **[x] The pair is installed and verified AT THE DRIVE (2026-08-04).** Confirmed by
      reading the binary's own banner on the rig, not by trusting the wizard:
      `~/.local/bin/cyanrip --version` →
      `cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)`, under
      Platterpus **v0.6.4b3**. It took b1 → b2 → b3 to get here: b2 added the
      diagnostics that made the failure visible, and b3 fixed what they revealed (the
      unexpanded `$HOME`). **This was the last precondition the round was waiting on.**
- **[ ] Run the rig session: H9, H10, H12, T9, T12, T13.** Capture **stdout for every
      invocation** — seven of the ripper's refusal paths fire before its logfile exists,
      so nothing in the archived log can show them, and its heartbeat lines are
      stdout-only too. Send the artifacts to **both** repositories. Their lap 8 adds one
      cheap step worth taking: run `-x` on a rip you can afford to lose first, since it
      is the least-exercised code in the binary.
- **[ ] Answer their lap 7 §4** — whether the seven stdout-only refusal paths should be
      fixed by opening the logfile earlier or documented in the contract as stdout-only.
      They asked for our view rather than assuming. Not blocking the session.

What we owe, and what waits on their answers:

- **[ ] The addendum must record re-read *attempts*, not only successful swaps.** Round 7
      §2c: our whole-disc log says track 3 `Secure re-read: not attempted` (true of pass 1)
      while our EAC-style log says "re-reads did NOT agree" (true of pass 2, and measured).
      Nothing in the archived artifact reconciles them, though our app log has the fact
      outright. Captured and not surfaced — our own rule. **Blocked on Q8:** whether their
      `-Z N -l <tracks>` invocation writes its own logfile we can cite instead of
      paraphrasing.
- **[ ] Send the A7/G2/H12 forced-error corpus.** Hardware-gated and deliberately not
      hand-assembled: a corpus built from my reading of their control flow is a fixture
      carrying my assumptions about their control flow. **Now runnable without re-derivation:
      `docs/hardware-test-checklist.md` §F3** gives the five states as five one-line commands
      with exactly what to record for each. Case 1 needs no disc and nothing is written.
- **[ ] H9 — a second gate-1 disc (checklist §F1).** One disc verified their pre-gap emission exactly
      (13 sub-channel entries, 1 lead-in, zeros on tracks 3/6/11/12, 9 `Gaps:` rows). One
      disc is an existence proof, not a range: a disc with a *non-zero* pre-gap on a
      non-first track is the case that could still fail. Hardware-gated.
- **[ ] H10 — send the `-x` force-overread log line (checklist §F2).** We ship the toggle; we have never
      captured the line it produces on a drive that accepts the command. Hardware-gated on
      the BDR-209D.
- **[ ] Pass `--consumer platterpus/<version>` on every rip.** Their lap-4 §7/§4: it is what
      puts our identity into the archived artifact, recorded verbatim with their log saying
      *"reported by the caller, not verified by cyanrip"*. Deliberately **not** shipped in the
      same batch as a protocol bump — it is an argv change, and the argv chokepoint is
      validated, so it lands with its own range check and test.
- **[x] Parse their two new logfile lines** — `Handshake:` and `Consumer:`, done
      2026-08-04 at schema v17, off the real rig artifact rather than a fixture (which
      would have been our guess at their wording). `rip.ripper_handshake_note` carries
      the binary's own compiled-in round state verbatim — the rig log says `round 7 lap 7
      OPEN, verdict HOLD -- NOT a released build` — which is a provenance claim
      *derivable from the artifact's content* and a second, **independent** witness
      beside `ripper_handshake_approval` (our verdict on the banner). When the two
      disagree, the disagreement is the finding.
- **[ ] Read the argv surface from their `PROVIDER-CONTRACT:` pointer, not round prose.**
      Their lap-2 §4 declined our remedy (correctly — the contract *did* change: flags
      38 → 39 with `-x`, derived rows 422 → 431, so the line we asked them to write would
      have been false) and offered something better: a generated `PROVIDER-CONTRACT.md` at
      the pin plus a resolvable `PROVIDER-CONTRACT: <path> @ <commit>` header. Read that
      file at that commit. Keep the walk-back as the *visible* fallback.
- **[ ] T14(c) — `Duration:` must agree with `Samples:` in both passes' logs.** Their
      three-part restatement of T14; (a) is done, (b) is blocked on Q8, (c) needs a
      `Duration:` field we do not yet parse. Queued behind that field rather than
      half-landed.
- **[ ] Re-run the argv-surface agreement test against their round-7 contract** once their
      §I lands. Their round-7 file has **no §I provider-contract section** (genuinely
      absent, not relettered), so `tests/test_argv_surface_agreement.py` walks back to the
      newest round carrying ≥ 30 published flags. Mechanical, and it is the check that
      would have caught the `-V` blocker a round earlier.
- **[x] T14 — the multi-pass rip end-to-end test. Done 2026-08-03.**
      `tests/test_multi_pass_rip_end_to_end.py`: a real `RipWorker` over a two-call fake
      ripper, pass 1 → AccurateRip miss on tracks 3 and 5 → `-Z 2 -l 3,5` → report written
      to disk, **re-read**, and run through the real `rip_audit`. Floors assert the second
      pass actually ran and the two argvs actually differ, so a fake that collapsed to one
      pass cannot make it green. Its own tamper case found a **new** defect: the
      argv-agreement check compared single-letter flags only, so a long option injected in
      transit passed as agreement. Fixed and revert-proven. Offered to the fork as T14.

### P1 — Open from cyanrip handshake round 6 (2026-08-03, closed on pin `2f950c8`)

Each item is either queued with the reason it is queued, or hardware-gated. Nothing
here blocks the v0.6.3 release; round 6 is CLOSED both directions.

- **[ ] Send the forced-error corpus (their G2 — the highest-value artifact we owe them).**
      Their fatal inventory is 115 strings, of which 83 are control-flow-proven and the
      rest rest on the wording of the message or on a `goto` label whose fatality neither
      side can settle from source. A run that *forces* each state and records the string,
      its exit code and the exact argv settles them empirically. **Hardware-gated, and
      deliberately not fabricated:** `Offset is unset!`, `Device does not support changing
      speeds!` and the `goto end` family need real device states on the BDR-209D, and a
      hand-built corpus would be a fixture carrying my assumptions about their control
      flow — the §4d failure again (`docs/testing.md` §5.ac).
- **[ ] Parse `Encoder:` and `CD-TEXT:` into the report schema, then off the ignore list.**
      Both are real archival facts the fork added for us, both currently on
      `_IGNORED_DISC_LINES` with a recorded reason. Queued rather than half-landed because
      a regex with no rendered home is dead code that reads as coverage. `Encoder:` is
      encoder provenance (which ffmpeg built the files); `CD-TEXT:` is tri-state
      (present / absent / unreadable-by-this-driver) and closes an EAC parity row. The
      fork's method for `Encoder:` — assert it against `ffprobe` output rather than
      against the line itself — is the one to copy. Note the populated disc-level form is
      richer than our golden reference shows (`present (English, 5 disc fields, 2 of 2
      tracks tagged)`), and there is now a per-track indented `CD-TEXT:` block too.
- **[ ] Surface `Cache model:` as a *modelled* figure, distinct from our measured verdict.**
      Deliberately NOT wired to `defeat_audio_cache` (KDD-25/29 — see the recorded reason
      on the ignore-list entry). If shown at all it needs its own row, labelled as
      paranoia's model with the drive unprobed.
- **[ ] Consume the progress line's `, errors - %i` segment.** Their P2a declares it and
      we ignore it, so we learn the error count only from the finished log. Surfacing it
      would let rip-progress say "reading, 3 errors so far" instead of looking healthy
      until the end. Note it resets per `-Z` pass, like the paranoia counters.
- **[ ] Migrate `I:` / `LRA:` off libavfilter's wording onto the fork's `(R128)` rows.**
      Their A5 delivery: `Integrated loudness (R128):` and `Loudness range (R128):` are
      fork-owned and stable, where the unqualified headings we currently read are
      libavfilter's and move when FFmpeg does. **The `(R128)` qualifier is required** —
      libavfilter prints the unqualified spellings in the same track block, so an
      unqualified pattern matches two different lines. Needs report-schema fields first,
      same reason as `Encoder:`.
- **[x] `Total time:` / `Duration:` MM:SS.FF → seconds.** Done 2026-08-03.
      `parse_cd_duration_to_seconds` discriminates on colon count per their P1 units block:
      three fields → milliseconds, two → CD frames (1/75 s). A frame field above 74 is
      **refused** rather than reinterpreted as hundredths, so a duration cannot quietly gain
      up to a second. Real-hardware confirmation that the shape is not length-dependent: a
      59:42 disc prints `Total time:     59:42.57`, two fields on a full-length disc, where
      our own comment had guessed cyanrip switches to `HH:MM:SS.mmm` for those. Tests read
      the committed golden reference's own duration rows rather than hand-written samples.
- **[ ] Consider a second per-track paranoia field for the non-converged passes.** The
      per-track counters report the *final* `-Z` pass only, which hides the evidence of
      difficulty that made `-Z` re-read in the first place. Raised with them as a design
      question, not a defect; our side would need a field either way.
- **[ ] The cancelled-rip log addendum, properly.** Their J2 is right that appending after
      `Log FUN512:` breaks `cyanrip -Y`, and the naive sidecar regresses bug #19 (the
      shipped-CRC statement lives in that text). Needs the real fix, not the sidecar.
- **[ ] Answer J7 (tag casing).** The maintainer's ruling, still open. Recommendation: state
      the convention explicitly in the contract rather than leave it implied.
- **[ ] Reinstate `--dirty` in the fork's build tag (round 7).** Previously "agreed, not
      asking"; round 6 delivered two consecutive golden references whose banners named
      commits three behind the pin, so the mechanism demonstrably fires. Ours is not
      exposed — the wizard detaches onto the pin in a tree it wipes — but the artifacts we
      *receive* are.

### P1 — Open findings from the 2026-07-29 audits (three parallel read-only passes)

Recorded with the mechanism and a concrete failure scenario each, severity-ordered.
Everything above P1 severity in these passes was **fixed in v0.5.18**; this is what
remains. None of these is speculative — each was traced to a file:line.

- **[ ] A swapped-in re-rip keeps the FIRST pass's AccurateRip verdict → a track can be
      reported "AccurateRip verified" when the shipped bytes were never checked.**
      `parsers/cyanrip_log.py` replaces `copy_crc` with the swap-addendum CRC but leaves
      `accuraterip_v1/v2` as parsed from the first pass, and `main_window_rip`'s merge
      deliberately keeps the first-pass AR block when the re-rip's log printed none.
      Scenario: auto-fix re-rips track 3 with `-l 3 -Z 4`, converges, and the re-rip log
      carries no `Accurip` lines (partial-disc rip, or the container's AR lookup failed)
      → `copy_crc` is the new bytes, the AR block is the old bytes, `accuraterip_verified`
      is True, and the banner / JSON / per-track table / EAC log all assert a
      verification that never happened. **This is the worst finding of the three passes**
      — it is the exact class KDD-30 exists to prevent. Hardware-gated on one question:
      does cyanrip emit `Accurip` lines under `-l`? Answer that first, then fix.
- **[ ] `_auto_force_stop` fires after EVERY cancel, and can force-kill and eject the
      WRONG drive.** `_on_rip_cancel` arms a 5 s timer; `_on_rip_finished` never disarms
      it. So 5 s after any cancel it runs even though cyanrip already exited on SIGTERM:
      it clobbers the real "Rip cancelled" status, ejects unconditionally, and because
      nothing holds the device any more `fuser -k` returns non-zero and the code falls
      through to a **broad, non-device-scoped `pkill -KILL cyanrip`** — reintroducing the
      cross-drive kill that #23 removed. Worse, `_do_force_stop` reads the drive picker's
      *current* device at fire time, so cancelling on `sr0` and switching to `sr1` within
      5 s force-kills and ejects `sr1`. Fix: disarm in `_on_rip_finished`, and capture
      the device when arming rather than when firing.
- **[x] Stale files in the album folder contaminate the next rip's verification.**
      The CTDB, FLAC-verify and derived-verify workers glob `*.flac` in the album folder.
      Scenario: cancel a rip (partial + one truncated FLAC), fix a track title, re-rip →
      "Replace" writes new filenames beside the old. CTDB then builds its TOC from 2N
      files (spurious "not in database"), FLAC verify decodes the truncated leftover
      (a ⚠ FAILED and a downgraded verdict on a clean rip), derived-verify's expected
      count doubles, and the checksum manifest records files this rip never wrote.
      *Fixed:* "which files did this rip write?" is now one shared answer —
      `platterpus.rip_files`, which reads the rip's own `.log` (the record that defines the
      album folder in the first place) instead of listing it. All five call sites ask it: the
      three verify workers, `checksums.compute_digests`, and `ctdb.diagnose.find_flacs`.
      Degrades to the old folder scan when no log names the files, but logs the downgrade and
      names any excluded leftover.
      *Closed out 2026-07-31:* the six **mutating** siblings now route through the same
      helper — `ui/main_window_rip.py`'s unknown-mode tagging, the colon-restore metaflac
      pass, the FLAC re-compress and the transcode input, plus **both** embed loops in
      `adapters/cover_art.py` (archive fetch and cover-art-from-a-file). These were the worse
      half of the bug: the verify sites only *read* a leftover, while these wrote this disc's
      metadata into it, re-compressed it, transcoded it into the library, embedded this
      album's cover in it, and reported the inflated count as "embedded in N track(s)".
      `_start_post_rip_processing` takes a `rip_log=` argument and the finish handler passes
      its already-parsed `RipLog`, so the log is read once and all six agree on one list.
      Regression test per site, each verified by reverting the fix.
- **[ ] Closing the window during a rip can freeze it for up to ~100 s.**
      `_stop_rip_on_shutdown` calls `drive_control.free_drive()` **synchronously on the
      GUI thread**: five subprocess steps each bounded at 20 s. A wedged drive hits the
      worst case. It also runs *before* the rip thread's own stop, so it eats the whole
      shared shutdown budget and guarantees the rip thread is abandoned.
- **[x] Abandoned `in_progress` reports are treated as legitimate priors.**
      `rip_compare.find_prior_report` filters on `same_disc` only, never on
      `outcome.status`. Closing mid-rip leaves the worker's `in_progress` snapshot on
      disk forever, and a later re-rip compares against it and warns about "tracks the
      previous rip didn't have" on a clean rip.
      *Fixed 2026-07-31:* `rip_compare` now classifies every report as
      complete / partial / abandoned from its own `outcome.status`
      (`report_completeness`). Abandoned (`in_progress`) priors are never
      auto-selected and the skip is logged; a cancelled/failed prior is still used
      (real CRCs — not discarded) but loses to any complete prior and is labelled,
      and a track the short side never reached no longer warns. A report with no
      `outcome` block at all (pre-v7) still counts as a finished rip.
- **[x] Tagging failures are invisible.** `apply_track_tags` logs per-file
      `MetaflacError` at WARNING and returns the successes; the caller discards the
      result. There is no signal, no status line, and no report field. Scenario: the disk
      fills during the metaflac pass → every FLAC ships untagged, the UI says Done.
      *Fixed 2026-07-31:* `run_unknown_post_processing` returns a `TaggingResult`
      (attempted / tagged / failing basenames / whole-pass error) and the post-rip daemon
      delivers it on a new `tagging_done` signal — the same shape as every other post-rip
      step. The GUI slot puts the failing count and names on the status line and in the rip
      log view, and stops the trust banner claiming ✓ (the *audio* claim is still true and
      the text says so — an untagged album is a metadata problem, not a rip problem). The
      failures derive by *difference* from the returned successes, which also catches
      `apply_track_tags`' other way of not tagging a file: a name with no leading track
      number, which it skips deliberately. In the JSON it is an `issues` entry
      (`tagging_failed`) rather than a new `verification` sub-block — `IssueBlock` already
      fits, and a new sub-block would change a key set consumers and tests pin exactly, so
      the schema version is unchanged.
- **[ ] No SIGTERM/SIGINT handler.** `closeEvent` is the only thing that stops the
      in-container reader, so a session logout or `kill <pid>` during a rip leaves cyanrip
      ripping with the drive's eject button ignored — the 2026-07-01 bug through a third
      door.
- **[x] `_launch_post_rip_daemon` doesn't guard `compute()`.** An escape kills the daemon
      silently, emits no signal, and `_post_rip_work_settled` then reads the dead thread
      as "settled", so the library move proceeds as if the check had passed. (The
      `threading.excepthook` added in v0.5.18 means it is at least *logged* now.)
      *Fixed 2026-07-31:* `compute()` is wrapped; a crash is logged **against its step** and
      recorded in `_post_rip_failures` (`{thread attribute: error text}`, written under a
      module-level lock because two checks can die in the same instant). The settlement gate
      itself now reads that record: `_poll_library_move` calls `_post_rip_failure_summary()`
      and tells the user which check did not finish *before* it files the album away.
      `_post_rip_work_settled` deliberately still returns True for a crashed check — its
      question is "is anything still touching the files?", and blocking on a crash would
      strand the album in the workspace forever. **Left open:** a crashed CTDB check leaves
      the "Verifying against CTDB…" status where it is, because there is no failure signal
      for the per-step spinners; and with no library folder configured the announcement never
      runs, so the crash is visible only in `log.txt` and the settled record.
- **[x] `--doctor` can report a false PASS on its most important check.** Done 2026-07-31.
      Fixed in both halves, because neither alone is enough: `CyanripImpl.version()` now runs
      `-V` with `strict=True`, so a non-zero exit arrives as a `RipError` instead of a string
      (the exit code is visible *only* inside the adapter — verified against cyanrip's source
      that `case 'V':` returns 0, so this cannot fail a working ripper); and
      `check_backend_routing` now requires a *recognisable version* in the output, via a new
      pure `version_banner()` that reuses the dependency subsystem's own `parse_version`
      (Critical rule #6). Empty output — previously reported as OK with the literal
      "(no version output)" printed as the version — and error chatter are now blockers that
      quote what the tool actually said, so `--doctor` exits non-zero. `version_banner` scans
      for the versioned *line* rather than taking line 1, because a cold Distrobox container
      prints its own startup chatter first (stderr is merged into stdout) — taking line 1
      would have failed a working-but-slow cold start. +10 regression tests, incl. both
      directions through `run_preflight`/`exit_code`.
- **[x] Version probes ignore the exit code.** Done 2026-07-31. `_run_version_command` now
      returns `ran_ok=False` for any exit code outside an accepted set (default `{0}`), so a
      failed run's numbers can no longer be parsed as *the tool's* version — reproduced first:
      with the fix reverted the cd-paranoia probe returns
      `ProbeResult(present=True, version=(19, 0))` from a `libcdio.so.19.0` linker error, and
      a dead-container cyanrip probe reports podman's version as cyanrip's. A rejected probe
      logs the exit code + the tool's captured output (flattened to one bounded line), which is
      the only place the *reason* was previously visible: nowhere. **Before making non-zero a
      hard failure, every probed tool's version-flag exit code was checked against upstream
      source** (all exit 0 — cyanrip `case 'V': return 0`, cd-paranoia `exit(0)` with the
      banner on stderr, flac/metaflac/ffmpeg 0); the real non-zero-on-`--version` convention
      (libcdio's shared `print_version()` → `exit(EXIT_INFO)` == 100, which `cd-info` and
      `cd-drive` do but `cd-paranoia` does not) is served by an explicit `accept_exit_codes`
      allow-list no caller needs today, so the next maintainer's fix is a per-tool code with
      evidence rather than a relapse to "any exit code counts". Evidence table in
      `docs/dependency-contracts.md` → *Version probes*. A cancelled probe (SIGKILL → negative
      code) also stops reading as an answer. +7 regression tests in `tests/test_deps_checks.py`.
- **[x] Lower-severity swallowed detail.** Done 2026-07-31, all three. `cover_art` no longer
      collapses every failure reason into "none found for this release": a new pure
      `no_art_message(reason)` gives each reason its own sentence (an offline user is told the
      archive could not be reached and that the release may still have art), an unrecognised
      reason names its own code instead of inheriting "none found", and the reason plus the
      fetch's raw diagnostic (`_fetch_front_cover_detailed` now returns a `detail` too) land in
      the log AND in `CoverArtResult.error`. `ctdb/decode.py` carries `metaflac`'s stderr tail
      + exit code into both the `RuntimeError` message (which `ctdb/verify.py` turns into the
      user-visible verdict) and the log, via a shared `_stderr_tail` helper also used for the
      `flac` decoder and the unparseable-output path. `transcode.py` logs both failure
      branches, worded differently: `rc != 0` names the exit code, `rc == 0` with no temp names
      the *absence* of output. All three paths stay best-effort — nothing new raises.
      Regression tests: `tests/test_cover_art.py`
      (`test_apply_network_failure_is_not_reported_as_no_art`,
      `test_apply_404_still_says_the_release_has_none`,
      `test_no_art_message_is_distinct_per_reason`,
      `test_no_art_message_names_an_unknown_reason_instead_of_guessing`),
      `tests/test_ctdb_decode.py` (`test_total_samples_failure_carries_metaflac_stderr`,
      `test_total_samples_unparseable_output_is_logged`,
      `test_decode_failure_carries_flac_stderr`), `tests/test_transcode.py`
      (`test_missing_temp_output_is_logged_with_the_reason`,
      `test_nonzero_rc_failure_is_logged_with_the_exit_code`) — each verified by reverting the
      fix and watching it fail.
- **[ ] Earn the `Make use of C2 pointers : No` row.** EAC logcheckers weight this
      heavily and a survey says libcdio-paranoia never uses C2 pointers — but that is a
      secondary source, and `test_does_not_fabricate_read_mode_or_c2_pointers` correctly
      blocked asserting it (attempted and reverted, 2026-07-29). Read libcdio's source
      or measure it, then assert with the evidence recorded beside the assertion. See
      [`docs/eac-parity.md`](docs/eac-parity.md)
      for the other ranked log-quality rows.

### P1 — Thread-cancellation follow-ups (opened 2026-07-29, from the v0.5.17 audit)

- **[ ] Give `run_capture` a killable child so the remaining no-cancel workers can actually cancel.** **Two** workers block and expose **no `cancel()` at all**: `MusicBrainzWorker` and `UpdateCheckWorker`. (Count corrected 2026-07-31 — this entry said "the five" and named `DependencyCheckWorker` and `DiscInfoWorker`, both of which gained real cancels on 2026-07-29, the same day the entry was written; `DriveListWorker` is the third name still on the ratchet but does **not** block — it only globs `/dev` and reads sysfs, so it is permanent-by-nature rather than debt. Re-derive the roster from `tests/test_qthread_ownership.py::_WORKERS_WITHOUT_CANCEL` before starting.) With no `cancel()`, `stop_thread` has nothing to call: `quit()` never reaches a thread blocked in a subprocess or socket read, and closing the window waits out its share of the shutdown budget and then **abandons** the thread. That is bounded and non-fatal — abandonment retains the reference and makes exit bypass interpreter teardown (`platterpus.hard_exit`) — but it is not cancellation, and a stalled network or cold container is exactly when a user closes the window.
      The fix is one change in the shared helper, not one per worker: port `run_capture` from `subprocess.run` (which hides the child, so there is nothing to signal) to `Popen` with **`start_new_session=True`** — load-bearing, because without it the child shares the GUI's process group and a `killpg` would signal the GUI itself — exactly as `adapters/cache_probe.py` now does, then thread a cancel through the workers. Note both remaining workers are **network**, not subprocess (urllib/musicbrainzngs), so `run_capture` alone does not reach them: there is no child process, and interrupting means closing the socket out from under the request. Different mechanism, same acceptance.
      **Acceptance:** each gains a `cancel()` that actually interrupts its block; the `_WORKERS_WITHOUT_CANCEL` ratchet in `tests/test_qthread_ownership.py` shrinks by one per worker and its upper bound comes down with it (the list may only shrink — CLAUDE.md rule 10's discipline). Deliberately its own cycle: it touches the helper every backend probe goes through, and this is the kind of change that has historically introduced the next bug when bolted onto the end of another one (`docs/testing.md` §5.s).

- **[ ] Hardware round for the v0.5.17 cancellation work.** The suite proves the mechanisms fire; only the Bazzite + BDR-209D rig with a real disc proves the **drive stops**. Watch specifically: (1) **Cancel, then quit within five seconds** — does the reader stop and does the eject button work? (2) **Force stop** mid-rip — recorded as *cancelled*, not *failed*, in the report and the signed log? (3) **"Set up drive"** at a small window size — any clipped text? (4) **Close the window mid-rip** — no abort. Flagged honestly as hardware-gated rather than implied by a green suite.

---

## P2 — future enhancements (post-P1)

Items that are technically achievable but represent significant effort, double the rip time, or otherwise belong after the P1 backlog has settled. Pull from here when there's a concrete user request.

- **[x] Edited track tags feed the unknown-album rip.** Done 2026-05-30. After a successful unknown-mode rip, `_on_rip_finished` now calls `run_unknown_post_processing`, which reads `TrackTable.album_metadata()` + `tracks()` (the placeholder rows plus any edits the user made) and writes them to the FLACs via the new `apply_track_tags()` — blank fields fall back to the `Track NN` / Unknown Artist / Unknown Album placeholders, and a typed year becomes a `DATE` tag. **Bug fixed in the same change:** the post-processing is scoped to the album folder whipper just wrote (the `.log`'s parent dir), not the configured output root — otherwise an `rglob("*.flac")` over `~/Music/rips` would have re-tagged every previously ripped album with this disc's metadata. (`apply_placeholder_tags` remains for the no-data path.) Note: edits only flow to **tags**, not filenames — the unknown template still names files `## - Track NN` (renaming-from-edits would be a separate feature).

- **Test & Copy dual-pass rip — DOWNGRADED (largely already delivered).** Re-evaluated 2026-05-30 during the EAC-successor research review: **whipper already performs a test read and a copy read per track and records both CRCs** (your T32 log shows `Test CRC == Copy CRC` for all 16 tracks, and `(try 2)` re-reads on mismatch). We already surface this as the fidelity summary ("all N tracks verified, Test/Copy CRCs match"). So the core guarantee EAC's Test&Copy provides is already in hand. The only delta would be EAC's literal *two separate full passes* of the whole disc — marginal extra assurance at 2× rip time. Not worth building unless a user specifically asks for the two-full-passes behavior; keep parked here.

**From the 2026-06-23 EAC-guide gap analysis (P2 ideas; [docs/archive/archival-extraction-guide-2026-06.md](docs/archive/archival-extraction-guide-2026-06.md)):**

- **[ ] AcoustID fingerprint fallback.** Identify discs that MusicBrainz can't match by disc ID via audio fingerprinting (needs a personal AcoustID API key + `chromaprint`/`fpcalc`). Would route through the dependency subsystem; honors Critical Rule #5 (GUI resolves, not the ripper).
- **[ ] Lyrics fetch + embed.** The guide tags `LYRICS=` from a file; we fetch none. A lyrics source behind a small adapter → embed via metaflac. Niche.
- **[ ] Embed the cuesheet in FLAC metadata.** whipper writes a sidecar `.cue`; FLAC can hold the cuesheet in a metadata block (`--cuesheet`). Nice-to-have for single-image rips.
- **[ ] WavPack hybrid (.wv/.wvc) output — evaluate only.** A lossy base + exact correction file is a clever archival/portability split, but it's orthogonal to the FLAC-primary thesis and neither whipper nor cyanrip targets it as cleanly. Note as an idea; likely **don't pursue**.

**Graduated out of the multi-format design-of-record when it was archived (2026-08-06):**

- **[ ] Embed the cover art *inside* the `.wv` (the one open item from the WavPack ship).** WavPack carries art as a **binary APEv2 tag** (`Cover Art (Front)`), and **ffmpeg's WavPack muxer accepts only a single audio stream**, so the shipped transcode path physically cannot embed it. Today's behaviour is a deliberate, working fallback, not a silent gap: whenever a non-embedding format is selected, art is wanted and the disc was identified, the GUI **force-writes the front cover to the album folder as `cover.<ext>`** — even in the default "embed" cover-art mode, which normally embeds in the FLAC and deletes the folder copy. So a WavPack rip *always* has a visible cover; it is folder-level, not embedded. Closing it means registering the standalone **`wavpack`** encoder through the dependency subsystem (Critical rule #6 — no bespoke install code) and routing `.wv` through it instead of ffmpeg, which also needs hardware validation that the resulting `.wv` shows its art in real players. **Deferred, not lost** — this row exists because [`docs/archive/mp3-wav-support-2026-06.md`](docs/archive/mp3-wav-support-2026-06.md) was archived and an open item inside an archived doc is an item nobody will read again. WAV is *not* part of this: RIFF cannot hold art at all, and the UI warns rather than pretending.

---

## Out of scope (not in P0, P1, or P2)

Listed here for clarity so they don't sneak in:

- Replacing whipper itself with a from-scratch ripper. *(Note: forking/combining whipper + cyanrip and maintaining our own engine is **not** ruled out long-term — it's under research in [docs/cyanrip-fork.md](docs/cyanrip-fork.md), revisiting KDD-18. "Build our own from scratch" stays rejected.)*
- **AccurateRip submission.** Policy-restricted, not technically impossible. AccurateRip's operators accept submissions only from EAC and dBpoweramp; any Linux tool implementing the upload protocol would have its submissions rejected. **AccurateRip *verification* IS in scope and already works** — whipper queries AccurateRip during every rip, the parser captures the v1/v2 confidence values, and the rip-progress widget renders them.
- **CTDB submission.** Likely subject to the same trust-gate as AccurateRip submission.
- **Tracker (RED/OPS/Orpheus) log acceptance — out of scope by design, not a gap.** Researched 2026-07: the gazelle logcheckers score by ripper identity (allow-list: EAC, XLD, whipper ≥ 0.7.3) before ever looking at audio quality, so an unrecognized ripper (cyanrip) scores 0 regardless of how clean the rip is — there is no honest partial score to chase. RED additionally requires a valid EAC checksum we refuse to forge. The alternative we invest in instead is the open-trust path (AccurateRip + CTDB + an honest unsigned log). See PLANNING.md **KDD-24** and `docs/eac-parity.md`. Only legitimate reopen routes: re-add whipper as an optional secondary backend for its native tracker-recognized log (reverses KDD-18, needs sign-off), or upstream advocacy to add cyanrip to a logchecker's allow-list — neither is being built.
- **HTOA (hidden track one audio) — explicit scope note.** Not pursued. HTOA discs are rare in practice and neither backend gives a clean, low-effort extraction path today (whipper's HTOA accuracy edge cases, issues #75/#82, are moot now that whipper is removed as a backend, KDD-18). Revisit only on a concrete user request with a disc in hand.
- Network features (NAS, Plex, Jellyfin, cloud)
- Library/catalog database
- DVD/Blu-ray support
- Windows or macOS support

---

*Last updated for Platterpus v0.6.12b4.*
