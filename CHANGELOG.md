# Changelog

**This is the single, authoritative record of all notable changes to
Platterpus** — add an entry to `[Unreleased]` in the *same commit* as any change.
Format follows [Keep a Changelog](https://keepachangelog.com/); the project
adheres to [Semantic Versioning](https://semver.org/); dates are ISO-8601
(YYYY-MM-DD). The version itself is single-sourced from
`src/platterpus/__init__.py` (`__version__`); at release time the `[Unreleased]`
entries move under a dated `## [X.Y.Z]` heading. (Design decisions live in
`PLANNING.md` KDDs and `docs/session-log.md` — not here.)

## [Unreleased]

### Changed
- **Handshake protocol v4 adopted, byte-identical** (`ed8ee62f…`), carrying both
  amendments Platterpus proposed in round 9 lap 2 — the exactly-once rule for what
  counts as one lap, and the exclusion of the lap that carries a digest — plus the
  fork's addition that makes the second one work: **the verifier excludes the lap
  it received, not its own newest**. Without that asymmetry the two sides drop
  different files and disagree permanently, which is our own amendment
  reintroducing the failure it was fixing. Round 9 is `GO` from our side on
  `b56f936`.
- **`scripts/emit_envelope.py`** — one file per exchange, restored after being
  deleted. Deleting our envelope removed our exposure; protocol v4 §5a's
  exactly-once rule removed everyone's, so the format is safe to use again. The
  generator asserts the not-a-lap property on its own output **before writing**,
  because a *single-part* envelope would otherwise declare each field exactly once
  and be indistinguishable from a lap.
- **The transport envelope's filename is now generated, not typed**
  (`emit_envelope.envelope_filename`), derived from the header of the lap it leads
  with — the same rule `handshake_filename` follows on the lap side, and for the
  same reason: a typed name is a second description of a fact the file already
  declares. The literal had drifted three times in one session
  (`round08platterpusbundle` → `round09platterpusenvelope` →
  `round09lap06platterpus`) with no gate noticing. The name is unchanged.

### Fixed
- **Closing round 8 moved the pin's approval attribution, and only a test noticed.**
  `handshake_approval.APPROVED_BY_ROUND` 7 → 8 and `APPROVED_FOR_PLATTERPUS_VERSION`
  `0.6.5` → `0.6.12b6`, both derived from the newest CLOSED round's own verification
  file. Every rip report and every EAC-compatible log stamps those two values, so
  closing a round has a **product** consequence and nothing else in the codebase
  would have seen it go stale. The old pairing was defensible rather than wrong —
  round 7's lap 41 declares `HANDSHAKE-PIN: 104f6d4` and records `ddf7ac3` as the
  release of *identical* C source (`git diff … -- 'src/*.c' 'src/*.h'` empty, "so
  `HANDSHAKE-PIN` does not move") — but round 8's laps declare `HANDSHAKE-PIN:
  ddf7ac3` outright on both sides, which is the direct attribution.
- **The test picking that verification file accepted the pin appearing anywhere in
  it.** `pin in text` is the "satisfied by the wrong thing" shape: round 7's lap 41
  contains `ddf7ac3` four times, and only one is a declaration — the others are a
  build tag (`platterpus-fork-gddf7ac3`) and prose about a `git diff`. It happened to
  select the right file, and would equally have selected a lap arguing *against* the
  pin or one whose only occurrence was inside another build's tag, then read the two
  report-facing constants out of it. Now the pin must be the first token of a
  **pin-declaring field** (`HANDSHAKE-PIN` or `HANDSHAKE-RELEASE`), fences stripped,
  with the build-tag and prose cases proven to be rejected.
- **Round 9 lap 8 now reports the close's three off-directory consequences to the
  fork**, including the one they read: the generated consumer contract's provenance
  header. A round close moved a gate verdict, two report-facing constants and a
  generated document, none of them in `docs/handshake/` — so the lap asks them to
  check what a close moves on their side too.
- **Round 8 is CLOSED.** Our lap 10 declared `GO` but could not close it: §5 requires
  the peer verdict *transcribed from the file they sent*, and we held none of their
  round-8 laps 3–17, so lap 10 recorded a relayed `OPEN` and failed closed —
  correctly. Those laps arrived inside the fork's round-9 lap-3 envelope;
  `round-08-lap-17.md` declares `GO`, and `verified/round-08-lap-18.md` now
  transcribes it from the file. The round sat open five days with **both sides
  declaring `GO`**, because one side could not see the other's declaration; the gate
  was right the whole time and the fix was never a change to the gate — it was an
  envelope. Round 8's digest is unchanged at `81415fe9a22d4884 over 12` (a lap
  excludes itself, so filing the closing lap does not move it).
- **Closed-set verdict fields are now emitted as bare tokens, enforced on output**
  (`handshake.closed_set_prose`). The fork's gate anchors its verdict pattern to
  end-of-line; ours takes the first whitespace-delimited token. So
  `HANDSHAKE-PEER-VERDICT: HOLD — transcribed from…` reads as `HOLD` to us and as
  **absent** to them — their gate reported *"our verdict GO, but no peer verdict
  declared"* on a lap that declared one. A closing `GO` their gate reads as
  verdict-less refuses a close both sides agreed to. Tolerant on input, strict on
  output, which is the argv-chokepoint rule applied to the handshake seam; the three
  laps of ours that already went out with prose are named in a frozen list with the
  reason, because a `SENT` lap cannot be fixed. The first version of the sweep
  omitted fence-stripping and flagged the fork's *conforming* lap 7 for quoting the
  bad shape inside a fence — §2 rule 2, broken in the tool written to check it.
- **`SENT_LAPS` recorded the wrong event, in both directions inside 48 hours.** It
  pinned a lap's hash at hand-over to the operator; that is not delivery to the peer,
  and only the operator can distinguish them. Lap 6 was edited as "not yet sent" when
  it had gone, and lap 8 was pinned as sent when it had not — asserting the fork held
  bytes they had never seen. Rows now record **operator-confirmed delivery**, and the
  lap-8 row was removed rather than corrected, because it was never a send. The
  concept neither spec has: v4 §4a makes `RECEIVED` claimable only by the recipient
  for exactly this reason, then leaves `SENT` to the sender — the one party who cannot
  observe it.
- **Round 9 lap 6 misquoted the fork's own document while correcting them.** Its
  §D lead attributed *"Committed to `platterpus-fork` at `003f7aa`"* to a §H of
  their lap 3 — that string appears nowhere in the file and there is no §H. The
  argument it supports survives untouched (their §I line 286 does name `fa7e319`
  as its own commit, and a file committed at X cannot contain X), but the quote
  is now verbatim with its line number, verified against the source. Caught by
  sweeping every hex token and quoted fragment in the lap against the inbound
  files before hand-over; the lap had not been sent, so it was corrected in place
  under v4 §4a rather than owing a correction lap. `SENT_LAPS` now pins it.
  When the envelope was retired on 2026-08-15 its test file went with it, and when
  `emit_envelope.py` re-created the envelope hours later the guard was not restored
  — leaving the two properties stated only in a source comment, which is the
  *"a comment where a check belongs is not a fix"* failure. `tests/test_handshake_file_naming.py`
  now pins both on the real file: the name cannot match `round-*.md` (the glob both
  projects' gates use to collect laps, checked case-folded too), and it satisfies
  CLAUDE.md → *Artifact filenames that cross machines*, asserted via
  `find_script.normalise` so the rule and the resolver cannot drift into two ideas
  of "safe". Each assertion is proven discriminating against the name it must
  reject.
- **`emit_envelope.py` had no test coverage at all** — its not-a-lap guard was
  written, documented, and never covered by a test. (Precisely: it *executes* on
  every emit and has **never refused anything**, because no committed state has a
  one-part envelope lacking the preamble declarations. An earlier wording here and
  in round-9 lap 6 §H said it had "fired", which is not derivable from any commit;
  corrected in lap 8 §A3.) Now exercised on the case it exists for — a one-part
  envelope, where the structural v4 §5a exclusion does not apply for free — with a
  revert-proof that the guard actually refuses, plus a round-trip assertion that
  every part splits back byte-identical to its original.
- **Round 9 lap 8 corrects three statements lap 6 shipped**, found by an adversarial
  review that finished *after* lap 6 was handed over: a `SENT_LAPS` count made false
  by the very commit that shipped it (five → six), a §B/§E self-contradiction about
  whether that lap travelled in an envelope or bare, and the "it fired" claim above.
  Lap 6 is not edited — it is `SENT` and frozen at `f2a86641…`, so the correction is
  a new lap per v4 §4a. Two lessons graduated with it: **finish the review before the
  artifact leaves, or the review becomes a correction lap**, and **a sweep beats a
  re-read** — "a number that was true when written" reads correctly however carefully
  you read it.
- **`test_our_published_round_9_numbers_still_reproduce` derived its exclusion set
  instead of listing it.** Reproducing a past digest declaration means excluding that
  lap *and every lap filed since*; the hand-written tuple went stale the moment lap 8
  was filed and reproduced a different number for lap 4. It failed loudly only
  because lap 4's value was pinned — with an unpinned lap it would have silently
  validated the wrong figure, which is the manufactured-mismatch failure one level
  up, in the test rather than the tool. Now derived from the tree, with all four
  published laps pinned and a floor that fails if a newer lap's declared digest goes
  unpinned.
- **The envelope no longer implies a send that did not happen.** `outbound/` held an
  envelope packing lap 6 *and* lap 2 while lap 6 actually went bare and §E declined
  to re-send lap 2 — one half of the §B/§E contradiction. `PARTS` now tracks the
  current lap only, the unsent lap-6 envelope is removed, and `emit_envelope.py`
  states that its output is the *offered* packaging while `SENT_LAPS` is the record
  of what was sent.
- **`round_digest.py --exclude` silently dropped nothing when its argument did not
  match**, printing a confident digest over the full set — including the lap it
  had been told to remove. A manufactured mismatch is indistinguishable from a
  real one, and this sat inside the tool implementing the one protocol rule
  neither project may override. It now refuses with exit 2 and is repeatable, since
  a verifier reproducing an older declaration must drop every lap filed since.
  **Found by running an adversarial review over a diagnosis before publishing it**,
  not by the tool's own tests — which only ever passed it names that matched.
- **A lap was edited after it had been sent.** Round 8 lap 10 was handed over at
  `c125acd1…` and two commits later carried an extra header line and an appended
  section describing a since-discarded draft — protocol v4 §4a in the plainest
  terms: *a sent lap is never edited; a correction is a new lap.* Found by the
  fork's cross-project checksum, not by us: every check we had was about a file's
  **content** and none about its **identity over time**. Restored to the bytes both
  sides hold, and round 8's digest now matches theirs exactly at
  `81415fe9a22d4884 over 12`. `tests/test_sent_laps_are_immutable.py` pins the
  hash of every lap we have handed over, with a failure message that says to
  restore the file rather than update the constant — a guard whose remedy is
  "adjust the guard" is not one.
- **The naming sweep and the round digest disagreed about what a lap is.** Both
  now use protocol v4 §5a's rule instead of a filename allowlist, at the two
  thresholds each needs: the digest requires each identifying field present
  exactly once (a lap with no round number cannot be placed), the naming sweep
  excludes only on *duplicates* (rounds 1–6 predate the fields and are still laps).

### Changed
- **Handshake protocol v3 adopted, byte-identical from the cyanrip fork**
  (`docs/handshake-protocol.md`, sha256 `63f53d05…`). Round and lap become *legal
  states*: computed round states with `RECONCILE` for a record mismatch, a
  terminal `CLOSED` that can never reopen, addressing fields that say which repo a
  lap came from and what it wants changed, convergence rules R1–R7, and operator
  overrides that are always available and never silent. **The provider opens a
  round** — the rule was settled by asking both projects the question
  simultaneously without either seeing the other's answer, and the fork wrote
  *our* argument into the shared file over their own: only the provider can mint
  the unit of work, because a round decides a pin and you cannot open a round
  against a commit that does not exist.
- **`scripts/round_digest.py` — `HANDSHAKE-ROUND-DIGEST`, implemented from the
  spec text and deliberately not from the fork's implementation**, so the two
  numbers are worth comparing. It found two things on its first run: our own
  transport envelope was being counted as a lap (a container is not a lap — the
  rule is now derived from the spec's own ambiguity clause rather than a
  filename allowlist), and our round-8 record holds 4 laps against the fork's 12,
  which is the §4a `RECONCILE` state the checksum exists to make visible.
- **The transport envelope is retired, and the reason is worth more than the
  feature.** It was added this cycle so an operator could send one attachment
  instead of three, and deleted the same day: a **lap file is the interchange
  format** — cyanrip sends plain laps and so do we — while a container carrying
  wire headers in its body is something *every content-based sweep on both sides
  must be taught to ignore*, one sweep at a time. It cost two lessons in one
  afternoon: the round digest counted it as a lap, and the naming sweep read it as
  a misfiled one. Round 9 lap 2 raises the underlying gap with the fork as a
  blocking amendment, because deleting our container does not remove the gap — the
  next one will not be ours.

### Added
- **The cue check now judges *where* an `INDEX 00` pre-gap marker sits, not only
  whether one exists.** A marker means *"this track's pre-gap is appended to the
  end of the file above"*, so the file above must be the **previous track's**
  audio. On a partial rip driven by the per-track "Rip?" checkboxes, cyanrip
  writes the marker even when the previous track was not selected — nesting it
  under whichever file happens to be current, at a position that file does not
  contain. Measured on the 2026-08-15 rig rip (`-l 1,3,5,6,7`): track 5's marker
  landed **682 frames — 9.09 s — past the end of track 3's file**, while track
  7's, whose predecessor *was* ripped, is exactly right. Both are in one cue, and
  both are re-derived from the two committed artifacts by the tests rather than
  transcribed. Three findings, so a bug report is pointed at the right cause:
  `cue_index00_orphaned`, `cue_index00_misplaced`, `cue_index00_past_eof`. The
  defect is upstream-origin (`90c02175`, 2023) and present in every cyanrip
  release either project has shipped; the fork disclosed it independently in
  round 8. The audio is unaffected — this is an error in the sheet.
- **`ExpectedCue.track_frames`** — each track's length in CD frames, derived by
  `rip_audit` from the ripper's own sector numbers, so the finding can say *how
  far* past a file's end a marker lands instead of only that it is wrong.

### Fixed
- **The cue parser attributed a file to the wrong track in the ordinary
  multi-file layout.** A `FILE` line seen while a track block was still
  syntactically open was always taken as that track's own audio — true in
  cyanrip's gap-appended shape (`TRACK`/`INDEX 00`/`FILE`/`INDEX 01`), and wrong
  in the plain one (`FILE`/`TRACK`), where it belongs to the *next* track. It
  now re-points only when the open track has an `INDEX 00` and no `INDEX 01`
  yet, which is that shape's signature. Invisible until something needed to know
  whose audio a file holds: on the rig cue it credited track 3's file to track 1
  and would have reported the misplaced marker as 8048 frames out instead of the
  true 682. Found by the new placement tests, not by review.
- **`--install-ripper list` — choose a cyanrip build instead of memorising a
  SHA.** Prints every build this Platterpus knows how to install, each with the
  **build tag** a correct build must print, the approved one first and marked
  `✓`, anything unverified marked `⚠`:

  ```
    ✓ approved: ddf7ac3 (platterpus-fork-gddf7ac3)
    ⚠ test-pin: cb440bd (platterpus-fork-gcb440bd)
  ```

  Naming the tag is the point, not decoration: it is what the binary prints and
  what `--rig-check` compares, so it is how a rip is traced back to a build
  later. A menu offering "the newest beta" would ask an operator to pick
  something they cannot identify afterwards — which is how a rig session
  produced a complete, clean artifact set for `g2ce8993` while the round under
  review was `ddf7ac3`.

  **Ordering is by trust, not by date, and only for the ripper.** For the app a
  newer release is a better one. For the ripper it is not: the build a closed
  handshake round approved is the one whose output both projects verified, and a
  newer test pin is by definition *less* checked. Listing installs nothing — a
  test asserts the installer is never even constructed, because the dangerous
  failure is not a wrong menu but a menu that replaces the ripper you are
  currently using.
- **`update_check.available_releases()`** — the list form of the existing
  "is there an update" check, for a picker that offers a choice rather than a
  single answer. It shares one parser and one ordering with `latest_release()`,
  which is now literally the head of that list: an offer list that disagreed
  with the update prompt about which release is newest would be worse than no
  picker. Respects the existing `update_channel` / `ripper_channel` settings,
  which already exist and are deliberately separate so you can run app betas
  against a released ripper, or the reverse during a hardware session.

### Fixed
- **A wrong cyanrip build is now refused *before* it is installed.** The install
  ran build → install → export → verify, so `sudo install` overwrote
  `/usr/local/bin/cyanrip` and `distrobox-export` rewrote the host wrapper
  *before* anything compared the binary's build tag. A failed verification
  reported the problem accurately and still left the wrong ripper on the ripping
  path with no rollback — the guard meant to be the last word running after the
  point of no return. The build step already read the banner off the binary it
  had just produced; it now compares it too, and refuses with both the tag it
  got and the tag it wanted, plus an explicit note that nothing was changed and
  the previous ripper is still in place. The post-install check stays: one says
  *we built the right thing*, the other says *the right thing is what landed and
  got exported*, and install/export is exactly where a correct build can still
  go astray. (Latent, not a sighting — no rig failure was caused by it.)
- **`--install-ripper` no longer appears to print its own source code at you.**
  Several steps pass a multi-line shell script as one `sh -c` argument, and the
  step engine logs each command at INFO, so a routine install emitted roughly a
  hundred literal lines of shell between the progress rows — and the log goes to
  the terminal as well as the file. Command lines are now escaped to exactly one
  line, losing nothing: newlines, tabs and returns become two-character escapes,
  which is reversible and greppable. Truncating would have been easier and would
  have thrown away the middle of the script, which is where the interesting part
  is. Applied to the failure and timeout paths too — a timeout is precisely when
  that line gets read.
- **The log did not record the arguments Platterpus itself was started with.**
  It records the exact argv of every dependency it spawns — a Critical-rule
  obligation — and the argv of a `--rig-session` run, but the main entry point
  logged only `platterpus X.Y.Z (build …) starting`. That gap cost a diagnosis
  on 2026-08-14: the rig's installed ripper silently changed from the approved
  pin to a different build, and the log showed a second start at the exact
  minute followed by the whole build/install/export sequence — but not *which
  pin it had been asked for*. The question could only be settled from the
  operator's shell history, which no bug report carries. The same reasoning that
  requires a dependency's argv applies to our own: this program's behaviour
  changes completely by flag, since `--install-ripper` rebuilds and replaces the
  ripper while `--doctor` touches nothing.

## [0.6.12b6] — 2026-08-15

### Fixed
- **Installing the approved cyanrip pin by name announced that no round had
  approved it.** `--install-ripper ddf7ac3` — naming the very build a closed
  round approved — printed *"NOT a pinned build, and no round has approved it"*
  and then *"NOTE: this is not the handshake-approved build (ddf7ac3)"*: a
  sentence of the form *"this is not X (X)"*. It also predicted that every rip
  would report `unapproved`. Ninety seconds later, on the rig, `--rig-check`
  reported **`OK ripper/handshake approved`** for that same binary — because
  approval is decided by the installed build tag, not by how the install was
  requested. Two surfaces disagreeing about one fact is the failure this
  project's rules name outright, and here the wrong one spoke first and loudest,
  at the moment an operator decides whether to trust the build they just made.

  The cause was a whole-object comparison. `target_for_commit` returns a
  `ForkTarget` whose `version` and `why` differ from the pinned target *by
  construction*, so `target != PRODUCTION_TARGET` was true even when the pins
  were identical. Approval is a property of the commit, so only the commit may
  decide it: both sites now compare pins through a `same_commit` helper that
  treats a short SHA and the full one as the same revision. The warning for a
  genuinely different commit is unchanged and has its own non-triviality test,
  because a "fix" that called everything approved would be worse than the bug.

### Added
- **`docs/cyanrip-known-issues.md` — ten verified issues to hand the fork,
  deliberately *not* a handshake lap.** The maintainer asked for something
  useful to send outside the open round 8, so it carries no wire header and no
  verdict: a document that looks like a lap gets counted as one. Every finding
  survived adversarial refutation and cites a committed artifact. Two concern
  the **provider contract itself** — it was not generated by the build it names,
  and its P2 table omits lines the shipped binary prints — which makes it the
  cheapest fix on the list, since every future staleness check depends on it.
- **The finding that matters most is about us, not them.** Of 26 candidates
  verified, **16 were refuted, and the dominant reason was *already fixed***:
  the cache probe, the `Done;` verdict line, the pregap LSN row, the `\:`
  escape, the `Total time:` unit, the `Peak level:` rename, and three more. Nine
  of the fork's shipped fixes were still described as open problems in our
  source comments, our ask list and our parity docs. A consumer whose
  documentation lags by four rounds sends work that is already done, and reasons
  about the dependency from a snapshot. The fix is to re-derive our half from
  their current contract rather than re-read our own — including the converse
  assertion we never had, that every rule we declare must still appear in their
  published contract.
- **Coverage is stated rather than implied.** 87 raw candidates from 7 evidence
  sources; 26 verified; **61 never individually checked and deliberately
  excluded**, because on the measured base rate roughly two-thirds would be
  refuted and sending a list with a known-poor hit rate costs the other side a
  lap. All 16 refutations are named — telling them what we wrongly believed was
  open shows which of their fixes never reached their consumer's docs.
- **The 2026-08-13 rig run is committed, so claims about it can be checked.**
  A real disc read on the Bazzite + Pioneer BDR-209D — cyanrip log, cue, our JSON
  report, the ui-script transcript and report, the `--rig-check` manifest, the
  argv probe, the app log and `--doctor` — now lives in
  `docs/handshake/artifactsround08/`. Text only, no audio (Critical rule #8: the
  per-track CRCs are the proof). It had been sitting outside the repo, which
  meant every statement about it was an assertion rather than a citation — the
  exact thing this project's *answer from the artifact* rule exists to prevent.
  Its README records what the run measured (`-s 667`, paranoia max, five of
  fourteen tracks, `Ripping errors: 0`, three accurately ripped and two
  offset-variant at confidence 200) and, prominently, **which build produced
  it**: `platterpus-fork-g2ce8993`, which is *not* the `ddf7ac3` under review in
  round 8. Our own `--rig-check` flagged that at the time and the notice is
  quoted verbatim, because evidence about one build is not evidence about
  another.
- **An accessibility conformance target, audited and now enforced.** The
  maintainer commissioned a UI/UX & accessibility standards review and asked for
  an audit against it *"so we do not regress"*. The target is **WCAG 2.2 AA**
  (also ISO/IEC 40500:2025), and the audit found the app already passing every
  criterion it could be held to — which is precisely when a rule is worth
  writing down, because a passing state with nothing holding it decays silently.
  `tests/test_accessibility_standards.py` now pins five of them: status is never
  carried by colour alone (every verdict level has a `✓`/`⚠`/`ⓘ` marker, checked
  by *calling* the real verdict function across five branches, not by grepping
  for glyphs); there are no single-character keyboard shortcuts (WCAG 2.1.4 —
  they fire while a speech-input user is dictating); help stays in one place
  behind the platform Help key; status announcements do not steal focus; and our
  own explicit widget sizing stays above the 24 px floor. Each check has a
  non-triviality floor, so none of them can pass by examining nothing.
- **What does *not* transfer is stated rather than quietly claimed.** The review
  targets web apps, so roughly half of it — `scroll-padding-top`, reflow to
  320 px, `role="grid"`, TV safe areas — has no desktop-Qt meaning and is
  explicitly excluded from the conformance claim. Two gaps are recorded as open
  rather than papered over: contrast has not been measured from rendered pixels,
  and the track table has not had a greyscale/CVD pass. Full audit,
  per-criterion results and the sizing numbers: `docs/ux-design-principles.md`
  → *Conformance target*.

### Fixed
- **The scroll-gesture guard now covers the control it was written for.** The
  first pass protected Settings and the script console — the two surfaces that
  happened to be under discussion — and left the **read offset** in the
  *Set up drive* dialog unguarded, which is the single value in the app where a
  stray wheel roll rips the next disc wrong with no error and a clean-looking
  log. Also guarded: the drive combo on the main window, where a scroll aimed at
  the page could silently switch which drive the next rip reads *and* re-trigger
  a disc scan. The host-setup and uninstall panes now hold your scroll position
  instead of yanking you back to the tail on every step, which is what they were
  doing at exactly the moment you had stopped to read a failing step.

  The real fix is that the rule is now **swept rather than applied by hand**: a
  test derives the population from the source and requires the guard, with two
  ratcheted allowlists carrying a written reason each. `rip_progress` keeps its
  own append path deliberately — its pane sits in a non-current tab where Qt
  leaves `maximum()` stale, so it tracks follow-state across appends instead,
  which is a *superset* of the shared helper — and a third test checks that
  claim is still true, so the exemption cannot outlive the reason it was
  granted.

## [0.6.12b5] — 2026-08-13

### Added
- **A scroll gesture can no longer change a setting.** Qt's default is that a
  spin box or combo under the pointer swallows the wheel and increments
  *itself*, so scrolling the Settings page past a control silently edited it —
  reported from real use: *"the scrolling on the settings page i have
  accidentially scrolled down on options i did not mean to."* For most apps that
  is an annoyance. Here it is a **data-integrity** defect: most of those controls
  are calibration that reaches cyanrip's argv, so a nudged read offset rips the
  **next disc wrong** and looks completely normal doing it — no error, no
  warning, a clean log with the wrong offset in every sample. Value widgets now
  ignore the wheel unless they already hold keyboard focus, so clicking into one
  and dialling still works and scrolling past does not.
- **The script console's transcript sticks to the bottom instead of resetting.**
  It follows the tail while you are at the tail, and holds position the moment
  you scroll up to read something — previously the next step dragged you away
  from the failure you had stopped to look at.

  Both live in one `ui/scroll_guards.py` applied by widget *type*, not patched
  into the ten controls that happened to be reported, and the wheel guard is
  measured against Qt's real behaviour: a companion test drives the same event
  at an **unguarded** spin box and requires the value to move, so the guard's
  other tests cannot pass by asserting nothing.

### Fixed
- **`pick-release` called a method `QTableWidget` does not have.** The picker's
  table is a `QTableWidget`, whose API is `setCurrentCell(row, column)`;
  `setCurrentRow` belongs to `QListWidget`. Written from memory rather than
  checked, and it raised `AttributeError` on the rig — so the operator still had
  to answer both dialogs by hand, on the run whose whole point was not having to.
  **Every test passed with the bug in place**, because the stand-in table
  cheerfully provided `setCurrentRow`: the stub was kinder than the product,
  exactly the shape `CLAUDE.md` warns about. The fake now offers only what the
  real widget offers, and a test asserts both halves — that `QTableWidget` has
  `setCurrentCell` and that it does **not** have `setCurrentRow` — so the fake
  cannot drift back into inventing API. Restoring the bug now fails two tests.
- **A `wait`-family predicate that raised was retried every tick, forever.**
  One `AttributeError` inside `pick-release` produced **25 identical ERROR rows
  for a single script line**, and the only thing that ended it was a human
  clicking the dialog. `_tick`'s catch-all recorded the fault and returned with
  the deadline still armed, so the next tick called the same broken predicate
  again. A faulting predicate now ends its step once, saying so. This is the
  worse of the two defects: a transcript with 25 rows for one line buries every
  other finding in the run.
- **`platterpuscollect.sh` ran without `set -e`.** Caught by the repo's own shell
  gate the moment it was committed. Not a formality: without it a failed copy of
  the transcript was invisible and the bundle would arrive *looking* complete
  while missing the evidence it exists to carry. Adding `set -eu` naively broke
  the script on a machine with no rips yet, so every command that may legitimately
  find nothing now goes through an explicit `optional` wrapper — "absent" and
  "broken" stay different. Exercised against two fake homes: a bare machine (exit
  0, bundle written) and a full one with a planted `.flac` (stripped).


### Added
- **`docs/rig-scripts/platterpuscollect.sh`** — one command that bundles a rig
  run's evidence into a single `~/platterpusbundle.tar.gz`: the script transcript
  folder, `report.json`, the app log, `--doctor`, both version banners, the config
  and the rig-check manifest, plus the newest rip's log/cue/report. **Text only** —
  it copies only known-text extensions and then sweeps for audio anyway and
  deletes what it finds (Critical rule #8), and that backstop was verified by
  planting a `.flac` and confirming it fires. Lives in the repo so it can be
  `curl`ed rather than attached: sending rig files through a chat attachment cost
  two runs on 2026-08-13 — once to a hyphen in the name, once to a browser's
  `(1)` suffix — and a raw URL with a published checksum has neither failure mode.

### Fixed
- **`docs/rig-scripts/round08joint.txt` named the EAC reference log by a path that
  was one space wrong**, so C6's `--verify-log` would have failed to *open* the
  file while `expect-exit 1` passed — a green result on the one test whose purpose
  is distinguishing "refused a foreign log" from "could not read it". Corrected
  against the operator's own `ls`. The general case (a literal path inside a
  script is an exact-match string, the same trap `find_script.py` fixed for
  `--run-script`) is queued in `TASKS.md`.

## [0.6.12b4] — 2026-08-13

### Added
- **`pick-release` — a script can now answer the MusicBrainz release picker.**
  A disc with more than one MusicBrainz candidate opens a modal and waits, which
  is right for a person and fatal for an unattended batch; the rig disc returns
  **four**, so the joint script needed an operator at the keyboard for its first
  minute and could not be left alone. `pick-release <mbid|prefix|N> [seconds]`
  waits for the picker, selects the named release and accepts it.

  **A verb rather than an app setting, deliberately.** Auto-choosing inside the
  product would silently pick the tags for every ambiguous disc a user ever rips
  — a real archival decision, and not ours to make on their behalf. In a script
  the choice is written down, appears in the transcript, and applies to that run
  only (`CLAUDE.md`: *a new testing capability is a script verb*).

  Three refusals, because the failure this prevents is a rip tagged from the
  wrong release — an error that survives into an archive: an MBID that is not
  among the candidates **fails and names what was offered** rather than choosing
  something else; an ambiguous prefix refuses rather than taking the first hit;
  and a row number is accepted but documented as the weaker form, since
  MusicBrainz ordering is not stable. Passing when **no** picker appears is
  allowed only alongside positive evidence that the disc identified — tracks
  loaded — so the verb cannot be satisfied by finding nothing.

## [0.6.12b3] — 2026-08-13

### Fixed
- **`--run-script` ran a *different* script when the named file would not load,
  and said nothing.** `load_file` returned `None`, so the launch path called
  `run_now()` regardless; an unreadable path left the editor holding the built-in
  starter sample, and that ran. The resulting transcript was correct about
  everything it said — right app version, right timestamp, real steps — and was
  about a nine-line sample the operator had never seen. `load_file` *had*
  reported the failure into the transcript pane; `_on_run` clears that pane as
  its first act, so the one sentence explaining what happened was erased about
  120 ms later by the very call that followed it. A file that will not load is
  now a refusal: nothing runs, the transcript says `REFUSED TO RUN` and names
  every directory searched, and a message box says so on screen for a launch
  nobody is sitting in front of. (Found on the rig, 2026-08-13, where it cost a
  run.)
- **A hyphen cost a rig run, so filenames no longer have to match exactly.** The
  same artifact is `round08joint.txt` on one machine and `round-08-joint.txt` on
  another — one spelling per project, for a file that crosses both. `--run-script`
  now resolves the path by comparing names with case and ASCII separators
  removed, searching the directory you named and then `~/Downloads`, `~/Desktop`
  and the working directory. It is symmetric, so neither project has to be the
  one that changes; it never guesses (two matches is a refusal that lists them);
  and a miss names every place it looked, because *"not found"* is only useful
  beside *where it looked*. Repo artifacts are also renamed to the separator-free
  convention now written down in `CLAUDE.md` → *Artifact filenames that cross
  machines*.
- **`expect-dialog none` could never pass, including in the sample shipped to
  teach the feature.** The script console is a `QDialog` and is open by
  definition while a script runs, so `_active_dialog()` always found it — the
  starter script a first-time reader is told to press Run on has always reported
  one failure. Worse and never shipped to a user: a `cancel` with no application
  dialog open would have found the console and *rejected* it, closing the window
  hosting the runner's own timer, mid-run. The console is the harness, not the
  application under test, and is now excluded.

## [0.6.12b2] — 2026-08-13

### Added
- **A script run now saves itself.** When a `--run-script` batch ends — normally
  or by being stopped — it writes `transcript.txt` and `report.json` into the
  same timestamped folder its screenshots go to
  (`~/.local/share/platterpus/uiscript/<stamp>/`), and the transcript's header
  names that folder. Until now the only way to get a transcript off the rig was
  the console's *Save transcript…* button: a person selecting text in a window,
  after an unattended run whose whole point was to need no person. On the
  2026-08-12 rig pass it came back pasted into a chat message instead. The
  answer to *"what do I send back"* is now one folder path. The Save button
  stays as the manual fallback for the case the automatic write fails (a full
  disk at the end of an hour-long disc pass must not also lose the run).

### Changed
- **`docs/rig-scripts/round08joint.txt` names 0.6.12b2 as its floor.** Its
  header said 0.6.12b1 was enough; it is not, because on anything older the
  SECTION D rip cannot start at all (see the drive-picker fix below), so a run on
  the older build yields a transcript that looks like a test result and tests
  nothing. Its closing lines also said *"send the transcript directory"* while
  nothing wrote a transcript into it — true as literally as it reads now. 93
  steps, 0 parse errors, 1 refusal by design.

### Fixed
- **The disc scan was killed four seconds into every launch, so no disc
  identified and no rip could start.** `DrivePicker.set_drives` re-emitted
  `drive_changed` even when the repopulate restored the **same** device — a no-op
  by definition. The main window's handler supersedes any in-flight disc probe,
  deliberately with a 0 ms wait (a probe blocked in a subprocess cannot be asked
  politely to stop), so the second populate SIGKILLed a healthy scan mid-TOC-read:
  `cyanrip exited -9`, no output, Start rip disabled, and a 72-step unattended
  script lost its rip and every step downstream (2026-08-12 rig run; the cyanrip
  fork logged the same three lines from their side as round 8 lap 7 §0b / J11).
  The 0 ms is not the bug and is unchanged — superseding really does need to be
  immediate. Asking it to supersede something for no reason was.
- **`wait-for-rip` passed instantly when no rip was running.** Its predicate is
  "no rip worker exists", which is equally true after a rip finishes and when one
  never started. On the rig it reported `ok` immediately after `rip` had failed,
  in SECTION D, in a transcript whose purpose was proving the rip happened. It
  now fails and says which state it found.
- **A refused `cyanrip` step left the previous invocation as the comparison
  subject.** Four times in one run, `expect-cyanrip` / `expect-exit` graded a
  command two lines earlier. It failed loudly that time, which was luck — the
  stale command could as easily have contained the expected string and reported
  a **pass for a step that never ran**. A refusal now clears the last-invocation
  state, so the following assertion reports *no cyanrip command has run yet*.
- **`expect-cyanrip` could not express a string containing a double quote.**
  cyanrip prints `Missing "=" in track metadata "1"`; every spelling of that
  assertion was unmatchable because quotes are grouping characters in the
  tokeniser and were consumed before the comparison. The fork reported it as *"a
  gap in the language, not in the test"* — correct. `Step.raw_tail` carries the
  verbatim tail and the match verbs use it.

## [0.6.12b1] — 2026-08-12

### Fixed
- **The release gate could not see a handshake round whose files were not yet
  committed, and four releases went out during one.** Round 8 ran for seven laps
  uncommitted, so `handshake.py --status` found no `round-8` files, reported
  every *filed* round CLOSED, and allowed a release — while being entirely
  correct about everything it could see. The existing empty-record guard did not
  fire: it only triggers when there are **no** rounds at all, and rounds 1–7 were
  right there. This is that same defect one level up — *an in-flight round with
  no files is indistinguishable from no round* — so `CURRENT_ROUND` is now a
  floor the status report counts unconditionally. Staleness fails safe: a value
  left behind blocks a release, which is a conversation; the other direction
  ships.
- **The end-to-end rip test raced the report writer and failed intermittently in
  CI.** v0.6.11 moved the 5.2 MB report write off the GUI thread; this assertion
  still read the file the instant the rip signalled done. It passed ~3,900 times
  and failed twice — the worst shape, because a flake in a merge gate teaches
  people to re-run rather than look. Not a product bug: `closeEvent` calls
  `_flush_rip_report(wait=True)`, so a real user's final report always lands, and
  every other test that reads a product-written report already flushed. The wait
  is **asserted**, not awaited blindly, so a genuinely stalled writer still fails
  with a message that says so instead of a confusing `FileNotFoundError`.
- **Every command Platterpus told you to type was wrong for AppImage users —
  seven strings, five modules.** The update dialog printed
  `platterpus --install-ripper <sha>`, the re-rip banner printed
  `platterpus --compare`, the CTDB no-match hint printed
  `platterpus --ctdb-calibrate`, and the User Guide printed three more (one of
  them a hardcoded `./platterpus-x86_64.AppImage` path). There is no `platterpus`
  on `PATH` for an AppImage install — the project's **primary** distribution
  channel — so each of those produced `bash: platterpus: command not found`. The
  cyanrip fork reported the update-dialog one as *the only thing that has
  actually blocked the operator, twice* (round 8 lap 7 §H). Every such string now
  goes through `build_info.self_invocation()`, which returns the absolute path of
  the running AppImage (quoted when it contains a space) and `platterpus`
  otherwise, so the line can be copied out of the window and run.
- The User Guide is now rendered by `help_content.user_guide()` rather than read
  as a constant, so its worked examples name the install you are actually using.
- **A `~/` path in a script reached the ripper as a literal tilde.** Nothing in
  the pipeline expanded it, so `cyanrip --verify-log ~/Music/…/rip.log` asked the
  ripper to open a file whose name starts with `~` — and the resulting failure is
  *plausible*, which is the dangerous part: a test asserting `expect-exit 1` goes
  green having proved nothing. A leading `~/` is now expanded in the arguments of
  the path-taking verbs (`set`, `cyanrip`, `rig-check`), **quoted or not**. That
  last part deliberately differs from a shell, where `"~/x"` stays literal: real
  album folders under `~/Music` need quoting *and* expanding, and following the
  shell would mean losing one to gain the other, silently either way. Free-text
  verbs (`log`, `expect-cyanrip`) are untouched — those carry match patterns, and
  rewriting a pattern changes what an assertion asserts.
- **`cyanrip --verify-log <path>` was refused from a script while the app itself
  ran exactly that argv.** `adapters/ripper_log_verify` has built
  `[cyanrip, --verify-log, <path>]` with no `-N` since v0.6.x, correctly — there
  is no metadata lookup to disable on a path that only checksums a text file — so
  the script surface could not test what the product does. The exemption is keyed
  on the fork's own published contract, which lists `-Y`/`--verify-log` under
  *Misc. options* (the same structural evidence that took `-x`/`-j` *out* of the
  probe set in 0.6.10), and it matches the **shape**, not the flag: exactly the
  flag plus one non-flag operand. `--verify-log x.log -d /dev/sr0` stays refused.

### Changed
- `docs/script-language.md` (generated) described the grammar as **"not
  quoted"**, which was never true — the tokeniser has always grouped a
  double-quoted value, and there is a test for it. The Syntax section now
  documents quoting and `~` expansion, and the machine half of the page carries
  `takes_paths` per verb so the prose and the JSON cannot disagree.

### Added
- **`rig-check` finds the rip by itself when given no folder.** The round-8 rig
  script carried the line *"Replace the path with the folder the rip actually
  wrote"* — a hand-edit standing in for something the program can do (maintainer
  directive, 2026-08-11). It now reuses `rip_compare`'s "which rip did the
  operator just make" rule, the same one `--compare` uses, rather than a second
  copy of it, and **names the folder it chose in the manifest** — a check that
  silently picked its own subject would let a reader attribute one rip's log to
  another. An explicit path still wins, and finding nothing is reported as its
  own row rather than left to look like a machine where discovery worked.
- **A script now says which ripper steps will be refused *before* step 1 runs.**
  A sanitiser refusal is a run-time outcome, so on a 60-step hardware batch the
  operator found out forty minutes in, standing next to a drive, with the disc
  pass already spent — while every fact needed was in the file before the run
  started. The findings go to the log at `WARNING`, to the top of the transcript
  above the step list, and into the run JSON. The run is not filtered or
  reordered: refused steps still execute and still record their own failure rows.
- `tests/test_self_invocation_sweep.py` — the fork found **one** instance; the
  sweep found **seven**, which is why this is enforced across the package rather
  than fixed at the site it was learned. It AST-walks every module, ignores
  docstrings (so the bug can still be *described* in code), and is revert-proved
  against `tests/data/hardcoded_invocations_prefix.json` — the seven pre-fix
  strings, generated verbatim from the blobs and carrying the commit they came
  from, so a weakened detector fails instead of passing by finding nothing.

## [0.6.11] — 2026-08-11

### Fixed
- **The 5 MB rip report was serialised and `fsync`'d on the GUI thread, six to
  eight times per rip.** `rip_report.write_report` was called inline because its
  own docstring said *"writing a small JSON file is cheap, so this is safe to
  call on the GUI thread"* — and that sentence is why nobody measured it for six
  releases. It is not a small file: the `debug` block alone is budgeted 8 MiB,
  and real reports on the maintainer's machine measure **5.2 MB / 46,594 lines**.
  Measured against that artifact: ~46 ms to serialise, 15–40 ms for the atomic
  write and its two `fsync`s on local SSD, and **206 ms** into a directory
  holding 400 MB of fresh FLAC writeback — which is exactly the post-rip
  condition, and the output folder is explicitly allowed to be a removable disk
  or a network share. The user-visible symptom was the results pane going
  unresponsive in bursts precisely as the verdict was being filled in.
  The write now runs on a dedicated worker (`report_writer.py`): one thread, a
  single newest-wins pending slot, ordering guaranteed by construction. Not one
  byte of the report changed — only when it is written relative to the event
  loop.
- **Two docstrings asserted the safety on size grounds and both were wrong.**
  Corrected in place rather than deleted, because they are the reason the defect
  survived: `rip_report.write_report` now says *do not call this on the GUI
  thread* with the measurements, and `atomic_write`'s "these are tiny files
  (< a few KB); the fsync cost is negligible" carries its own refutation.
  `tests/test_report_writer.py` fails if either claim returns unqualified.

### Changed
- **`closeEvent` waits — bounded — for the pending report.** The write is
  asynchronous now, so the final revision would otherwise die with the process.
  It waits up to `report_writer.FLUSH_TIMEOUT_S` and **logs when it times out**
  rather than returning silently, because a caller that cannot tell a completed
  write from an abandoned one reports the report as complete.

## [0.6.10] — 2026-08-11

### Fixed
- **`-x` and `-j` were exempt from the `-N` requirement, inverting the cyanrip
  fork's own contract.** `sanitise_cyanrip_args` treated them as probes that
  "print something and exit", so a scripted `cyanrip -x` was waved past the
  metadata chokepoint — and it is not a probe: the fork's published provider
  contract lists `-x` (row 40) and `-j` (row 42) under **Ripping options**, not
  under the metadata options where the genuinely non-ripping `-I`/`-J` live.
  Bare, they are rips with cyanrip's own MusicBrainz lookup **enabled**, which
  blocks on an interactive prompt with no terminal attached — the exact
  unattended hang the sanitiser exists to prevent. Reproduced end-to-end against
  the real `ScriptRunner`: the step stalls to the 300 s timeout, reports exit
  `null`, and leaves a partial album directory behind in the working directory.
  Every other `-x` call site in this repo already passed `-N`, so the convention
  was right everywhere and only the exemption was wrong. The test asserting the
  exemption was correct is what made it look verified for a release — it
  measured a belief about the flag rather than the fork's contract.
- **One probe flag anywhere exempted the entire command line.** The check was
  `any(arg in PROBE_FLAGS ...)`, so `cyanrip -v -d /dev/sr0 -o flac` — a full
  rip of the inserted disc with lookup on — was classified as a probe. It is
  `all(...)` now, with an explicit empty-argv guard, because `all()` over an
  empty sequence is `True` and would otherwise have made a bare `cyanrip` the
  most exempt invocation of all.
- **The version flags in `PROBE_FLAGS` are imported from `cyanrip_cli`** rather
  than spelled a second time. Caught by `tests/test_cyanrip_version_flag.py`,
  the gate added after upstream's `-V` removal made every hardcoded probe report
  the ripper as missing.
- **The `rig-check` verb rejected every real album folder.** Declared
  `max_args=1` while its handler already called `step.joined()`, so a path like
  `~/Music/The Police/Every Breath You Take` failed at *parse* time and never
  reached the handler. Every test had used a `tmp_path` with no spaces in it —
  a fixture tidier than reality, hiding the defect. Now rest-of-line, like
  `album`, which takes the tail for the same reason.
- **The shipped round-8 joint script carried the bare `cyanrip -x` on a live
  line.** Replaced with the fork's own info-only form
  (`-d /dev/sr0 -I -N -A -U -P 0 -x`), and the sanitiser now refuses the bare
  one rather than trusting whoever writes the next script.

### Added
- **A double test rip needs no paths typed.** `platterpus --compare` with **no
  arguments** now finds the newest rip and the best earlier rip *of the same
  disc* and compares them; `--rig-session` runs it, so ripping a disc twice and
  getting the diff stays one argument-less command. Pairing is by **disc
  identity**, never by recency alone — a naive "two most recent reports" rule
  would diff two different albums and print a confident table doing it. The
  existing `find_prior_report` does the ranking (completeness before recency,
  never an abandoned in-progress snapshot), so nothing about "same disc" is
  re-decided.
- **`rip_compare.default_report_roots()` / `newest_report()`** — one home for
  "where do rips live on this machine". The same list was being rebuilt in shell
  inside `rig_session.sh` twice and a third copy was about to be written; three
  descriptions of that will eventually disagree, and the one that disagrees
  silently searches the wrong place and reports *no rip found*, which is
  indistinguishable from *no rip happened*.

### Fixed
- **"Nothing to compare" now says which of four things happened** — no reports at
  all, only one rip, none of the same disc, or a newest rip carrying no disc
  identity. The operator acts differently on each, and a bare "nothing found"
  collapses them into one useless message.
- **The discovery label names the folder, not just the filename.** Two passes of
  one disc always produce the same basename, so the first version read
  `Album.platterpus.json -> Album.platterpus.json` and identified neither rip.

## [0.6.9] — 2026-08-11

### Fixed
- **The `rig-check` script verb rejected every real album folder.** Declared as
  taking at most one argument, while its handler was already calling
  `step.joined()` — so the verb's advertised arity contradicted its own
  implementation, and a path like `~/Music/The Police/Every Breath You Take`
  failed at PARSE time with an arity complaint, never reaching the handler.
  Every test had used a `tmp_path` with no spaces in it, which is exactly the
  gap a stand-in tidier than the real thing leaves invisible; it surfaced the
  first time a script named an actual album. Now rest-of-line, like `album`,
  which takes the tail for the same reason: a verb whose argument is human text
  takes the text.

### Added
- **`docs/rig-scripts/round08joint.txt`** — the joint round-8 test script, and
  the only file either project sends. Platterpus owns sections A, B and D;
  section C is fenced for the cyanrip fork to fill with tests only they can run
  (`-x` on a real drive, their new fatal messages, the malformed-argv shapes that
  segfaulted). It carries the entire verb vocabulary and the four rules that bite
  — `-N` required on rip invocations, no newline/NUL in arguments, no test that
  can pass by finding nothing, no assertion that can pass for the wrong reason —
  so it needs no companion document to be usable.

## [0.6.8] — 2026-08-11

### Changed
- **The cyanrip test pin moved to the round-8 build `cb440bd`** (`0.9.4-rc1+platterpus.6-beta.1`),
  with round 7's final pin `104f6d4` retired. This changes no verdict — a test pin is still
  reported `unapproved`, which is the correct answer while a round is open — it changes the
  *reason* the report gives, so a rip made during the round-8 session says "this is the round-8
  test pin, expected during a test session" instead of naming a pin from a round that has closed.
  Recorded alongside it: their lap 1 names the pin as `release-manifest.json` **seq 12**, but the
  manifest at `cb440bd` still reads `latest_seq: 11` with both channels at `ddf7ac3`, and
  `cb440bd` is not on `platterpus-fork` — so the machine-readable channel cannot see the pin it
  is supposed to publish. The pin itself builds and verifies; only its publication is missing.
- **A retired test pin no longer claims to be from the current round.** The message read
  "a round-{N} test pin that has since been RETIRED" using the constant that names the round of
  the *current* pin — so every previously-retired build was silently relabelled into the new
  round the moment one closed. It now says "an EARLIER round" and names only the round it can
  actually vouch for.

### Added
- **The cyanrip seam check, reachable from the script language and from a
  command line.** The fork's seam packet (2026-08-10 §4b) asked for a checker
  they could call from their own script so both projects append to **one**
  `MANIFEST.txt` instead of producing two piles to reconcile. `rig_check.py` is
  that. Its headline check is theirs and it needs no disc: compose exactly the
  argv a real rip would send — through the *real* argv builder, so a flag that
  stops being emitted disappears from the check on the next run — invoke the
  ripper against a device that cannot open, and read `invocation` back out of
  cyanrip's own `-j` record. That compares what the binary **received** against
  what we **composed**, which is the comparison a unit test of the builder
  cannot make. It also classifies the installed build tri-state, reads the
  `Handshake:` note in both its closed and open shapes, and parses the album's
  log with a floor (zero tracks is a `FAIL`, because a parse that finds nothing
  is not a parse that found nothing wrong). Four statuses, and the distinction is
  load-bearing: **`SKIP` means did not run**, so a session that never found the
  rip cannot render as one where everything passed.
- **`rig-check [album-folder]` script verb.** Runs on a helper thread with a
  bounded wait, like the `cyanrip` verb — the check spawns subprocesses, and the
  never-block rule has no case exemption.
- **`--rig-check` / `--rig-check-album` / `--rig-check-device`**, the interface
  the fork's script calls. Both surfaces are thin callers of the same function;
  neither reimplements it, so they cannot disagree about what the check found.
  `--rig-session` now runs it too, so an operator's one command still covers it.

### Changed
- **A new testing capability is a script verb; a CLI flag now has to be argued
  for.** Maintainer directive: the script language exists precisely so testing
  capabilities live there, and a capability the language cannot reach is one the
  tests cannot reach. `CLAUDE.md` carries the rule and
  `tests/test_script_surface_is_the_default.py` enforces it — every flag is
  listed with the reason a verb could not serve it (pre-GUI, an external caller,
  or the entry point that starts a script run), the list may shrink and not grow,
  and a fourth test refuses a free-form reason that merely reads like one of the
  three.

## [0.6.7] — 2026-08-11

### Fixed
- **A killed subprocess's output was captured and thrown away.** Asked by the cyanrip
  fork (seam packet 2026-08-10, T-C) after a `cyanrip -I` probe was killed at 120 s and
  the diagnostic record showed `exit code: none` with nothing captured. The answer was
  the bad one: `KillableCommand.run` caught the timeout, killed the group, called
  `communicate()` a second time to reap — which **returns everything buffered before the
  timeout** — ignored the return value and re-raised. `subprocess.run` has always done
  this correctly; ours was the one path that did not, which is why swapping `run` for a
  killable child silently lost the capture. Both streams are now attached to the
  exception and merged into the diagnostic (`run_capture` read `exc.output`, which
  aliases stdout only). Revert-proving it exposed a second defect: on the **unreapable**
  path CPython leaves raw *bytes* on the exception, and concatenating them would have
  raised `TypeError` inside the diagnostic path — decoded defensively now. Tri-state
  kept: an unreapable child still reports nothing recovered, and the message says which
  of the two silences it is.
- **The AccurateRip inventory check over-stated its own denominator.** Shipped in v0.6.6
  as a fix for under-counting, and it reported `29 of a possible 42` on a 14-track disc —
  implying 13 absent results where exactly **one** track could have had a 450 line at
  all. `Accurip 450:` prints only where v1 and v2 both missed, so the ceiling is
  `2 × tracks + (tracks where both missed)`, not `3 × tracks`. The same disc now reads
  `29/29 — complete`. Corrected against the fork's rule (seam packet §2.3); a ceiling
  that cannot be reached is as misleading as a subset reported as the whole.
- **The EAC-compatible log stated a cause the ripper never reported.** "Appended
  silence … *because the drive could not read that far*" was our inference; cyanrip
  reports the append and says nothing about why (seam packet §2.4). The fact stays, the
  guess goes — same discipline as `Cache defeat:` → `Cache model:`.

### Known, accepted, not yet fixed
- **The EAC-compatible log does not record that an earlier read disagreed.** When the
  auto-fix re-rips a track, the `Test CRC == Copy CRC` pair describes the secure
  re-read — truthfully — while the superseded first pass, which read something
  different, survives only in the addendum that log never mentions (seam packet §2.2;
  finding accepted, their diagnosis confirmed). Not fixed here: the exporter has no
  access to the superseded CRC, so it is a data-plumbing change, and one is not being
  made on the eve of a hardware session. First item in round 9.

### Fixed
- **The offset-variant footnote counted the first pass, not the tracks actually shipped.**
  Found on the first disc ever to take the auto-fix path on a released build (the Police
  re-rip, 2026-08-07). Tracks 3 and 5 both missed AccurateRip on the whole-disc pass and
  were re-ripped; track 3's re-read matched exactly, track 5's still matched only the
  +450 offset-variant pressing. So the truth afterwards is **one** partially-accurate
  track — which the verdict banner said, while the footnote directly beneath it said
  **"2 of 14"**. Both went into the same `.platterpus.json` and onto the same results
  pane, and the stale one reads as the more specific.

  `partially_accurate_summary` was a sentence rendered while *parsing* the whole-disc
  log and never recomputed once the addendum superseded those tracks' AccurateRip
  results. `accuraterip_counts` documents itself as the single source "so the banner,
  the JSON, and the reconciliation line can never disagree on the tally" — this field
  was the one bypassing it. It now counts through that function, in both the report and
  the results pane. `partially_accurate_reported` is deliberately left alone: it is the
  ripper's own fraction, verbatim, and being exactly that is its whole job.

  Two notes on how the fix was checked, because both mattered. The first regression test
  passed against a revert — it called the helper directly, and the helper was never what
  broke; it now goes through the real `build_report`. And the first fix *removed* the
  footnote entirely for logs that carry no ripper fraction (whipper-era and partial
  parses); the existing UI tests caught that, and it now falls back to the parser's
  sentence rather than going silent. Suppressing a right answer is not an improvement
  over correcting a wrong one.

## [0.6.6] — 2026-08-07

### Fixed
- **Every rip since v0.6.4 stamped the wrong handshake round into its archival record.**
  When round 7 closed, `FORK_PIN` moved to the round-7 release and a test derived from
  `docs/handshake/` confirmed it — while `handshake_approval.APPROVED_BY_ROUND` and
  `APPROVED_FOR_PLATTERPUS_VERSION`, one import away, stayed at `6` and `"0.6.3"`
  (untouched since v0.6.4b4). So v0.6.4 and v0.6.5 both wrote *"handshake round 6
  approved, verified by both projects, for Platterpus 0.6.3"* into every rip report, log
  and EAC-compatible export — about a pin that round **7** approved. Round 6 approved
  `2f950c8`, a different commit entirely.

  **Why nothing caught it:** both tests touching those values asserted
  `str(APPROVED_BY_ROUND) in approval.detail` — that the number printed is the number
  held. That passes for every possible value, including a wrong one. *A list checked
  against itself is consistent, not verified.* The constant one line away in
  `fork_source` had a real check against the record, and it was that check which moved
  the pin correctly. `test_the_approval_round_and_app_version_match_the_record` now
  derives both values from the newest **closed** round's own verification file, so the
  round, the app version and the pin move together or the suite fails.
- **`docs/dependency-contracts.md` said `-x` does not exist in cyanrip.** True when
  measured (2026-07-21, against 0.9.3.1 and upstream master) and false two weeks later:
  the fork added `-x` / `--cache-probe` in round 7 lap 1, at our own round-5 request. The
  correction is a block quote rather than an edit in place because confusing it with `-O`
  is a **hardware hazard**, not a documentation nit — `-O` is overread, and overread is
  the flag confirmed to hang the Pioneer BDR-209D for ~23 minutes. `CLAUDE.md`'s *state
  the range a contract claim covers, not the snapshot*, caught in our own document.

### Added
- **The test-script language can now drive a rip.** Eleven verbs that were listed in the
  vocabulary as *NOT YET IMPLEMENTED* are implemented: `rescan`, `album`, `album-artist`,
  `select-tracks`, `rip`, `wait-for-rip`, `cancel-rip`, `expect-tracks`, `set`, `expect`,
  `expect-contains`. Until now the surface could open dialogs and probe the ripper but
  could not start a rip — so the one thing a rig session exists to do still needed a
  person. Every verb reaches the **same slot a click reaches** rather than building its
  own version of the action, for the same reason the `cyanrip` verb is a real passthrough:
  a harness that is simpler than the product makes the product's gap invisible.
  - `set`/`expect` are keyed on the **`config.toml` field name**, not the dialog's row
    label — a row label is display text, and a script keyed on it breaks for reasons
    unrelated to the setting. Every `set` is checked by the same pure validator the
    Settings dialog uses, so a script can never persist a value the dialog would refuse.
  - `select-tracks all|none|1,3,5-7` is the per-track half (cyanrip's `-l`), with ranges,
    because a re-rip of "the tracks that failed last time" is the real use and spelling
    out 1-14 by hand is where a transcription error enters.
  - `wait-for-rip` is non-blocking — it arms the runner's deadline with a predicate, so a
    50-minute rip proceeds with the event loop running. A `sleep` there would freeze the
    window for the whole rip and break the thing being measured.
- **`docs/script-language.md` — the generated language reference.** The dictionary, the
  ruleset and the worked examples in one place: every verb with its arity and safety
  class, every dialog, every numeric limit, every settable field, the passthrough rules,
  eight rules for writing a script worth running, an annotated example, a recipe table,
  how to add a verb, and what each outcome means. **Both audiences in one file** — prose
  for a person and the same facts as JSON for a machine, emitted from one pass so they
  cannot disagree. Generated from the vocabulary table, the runner's live constants and
  `Config`'s own fields, and it carries the app version in both the footer stamp and a
  machine-readable field, so it is *truthful for the build it ships with*. Staleness is a
  test failure, not a review item.
- **`docs/rig-scripts/` — runnable hardware-session scripts**, starting with
  `police-rerip.txt` for the first rip on the round-7 release. Its shipped example is
  parsed by the **real** parser in CI and asserted to keep its floor (`expect-tracks`
  before `rip`), because the example teaches by being copied and a script without a floor
  rips whatever happened to be loaded — including nothing — and reports success.
- **Two audit checks the cyanrip fork asked for**, as rows in the existing `--audit-rips`
  registry rather than a new script: `handshake_note` cross-checks the ripper's **own**
  compiled-in round statement against *our* verdict on the same binary (two independent
  witnesses, and the released build is the first ever to emit the closed/GO shape — a
  transition nothing had exercised); `checksum_inventory` **counts** the checksums and
  states the denominator, after the fork's own comparison returned 4 where the real
  inventory was 12 and passed truthfully about a third of the evidence.
- **Help → Check for cyanrip updates**, and a `stable`/`beta` ripper channel in Settings.
  Reads the fork's published `release-manifest.json` and reports whether a newer fork
  build exists. **It never installs anything** — taking a ripper no closed round has
  verified makes every subsequent rip report `unapproved`, so the offer states the cost
  and a person decides. Ordering is by the fork's monotonic `release_seq`, never by the
  version string (theirs is upstream's plus SemVer *build metadata*, which the spec says
  must be ignored for precedence — a version comparison would see equality forever and
  never offer an upgrade); the channel is read from the manifest, never sniffed from the
  string (we spell a pre-release `b1`, they spell it `-beta.1`); and an unimplemented
  `schema` is refused rather than guessed at. The `commit` field is an **argv chokepoint**,
  not merely parsed data — it becomes a `git checkout` argument inside the container, so
  anything that is not a bare lowercase hex sha is refused.

## [0.6.5] — 2026-08-07

### Fixed
- **The setup wizard built a cyanrip commit that fails 2 of its own 33 tests.** `v0.6.4`
  shipped hours earlier pinned to `422d12a`; the fork withdrew it as the build to fetch and
  we confirmed why in their repository rather than accepting it. That commit bumps the
  version to `+platterpus.5` while its **in-tree golden reference and provider contract still
  describe `beta.8`** — the reference banner reads
  `cyanrip 0.9.4-rc1+platterpus.5-beta.8 (platterpus-fork-g92ceeed)` against a
  `+platterpus.5` build. Two of their gates exist for exactly that and both fired.

  **The binary was never the problem.** `422d12a` produces a correct program with the right
  version and the right `Handshake: round 7 lap 38 closed, verdict GO`; no rip made with it is
  suspect and nothing needs re-ripping. The failure is visible only to someone who *builds
  from source and runs the suite* — which, because our wizard builds from source, is every one
  of our users. That is why it is a release and not a footnote.

  The pin is now `ddf7ac3`, the first commit whose version and derived artifacts agree.
  `git diff 104f6d4 ddf7ac3 -- 'src/*.c' 'src/*.h'` is empty, so this is the same approved
  code and `HANDSHAKE-PIN` does **not** move — it is still `104f6d4` on both sides. `422d12a`
  joins the superseded list so a rig that already built it keeps receiving `--consumer`.

  **The rule both projects took from it:** choose the released commit *after* the derived
  artifacts agree, never at the version bump. Bump-then-regenerate guarantees one commit
  exists whose own suite fails, and regenerating in the same commit does not fix it — a
  generated artifact cannot contain the hash of the build that produced it. The remedy is
  *when* the release is announced, not how it is built.



## [0.6.4] — 2026-08-07

**Round 7 of the cyanrip handshake closed** — the first jointly-verified pair this project
has ever shipped, and the first release the handshake gate has ever allowed. The cyanrip pin
moves to the round-7 release `422d12a` (`0.9.4-rc1+platterpus.5`), and the `bN` suffix is
gone.

### Changed
- **The cyanrip pin moves to `422d12a`, the round-7 release** — not to `104f6d4`, the commit
  the round approved, and the difference is deliberate and recorded in
  `docs/handshake/verified/round-07-lap-40.md` §A. cyanrip bakes its handshake state in at
  build time, and `104f6d4` was built while the round was open, so every log it writes says
  `round 7 lap 33 OPEN, verdict HOLD -- NOT a released build` — we have one, from the J1 rip.
  That was true when it compiled and is false now; shipping a stable Platterpus whose every
  archival record carried it would be the worse of the two errors. Verified rather than
  inferred before taking it: their release golden reference parses clean through our
  production parser, and **all twelve `EAC CRC32`/`Accurip` lines are byte-identical** to the
  `104f6d4` reference we already hold.
- **The setup wizard builds the release again** (`WIZARD_TARGET` back to `PRODUCTION_TARGET`).
  It had pointed at the round-7 test pin since the beta line began.

### Fixed
- **The new pin was not in the `--consumer` accept-list, and nothing would have crashed.**
  `BUILD_TAGS_ACCEPTING_CONSUMER_FLAG` deliberately excluded `FORK_PIN`, with a comment
  explaining that the pinned r2 build predates the flag. That was correct and became false
  the instant the pin moved to a build which does accept it. Every rip on the new pin would
  simply have stopped recording who drove it — the provenance line the whole seam exists to
  carry — with no error anywhere. Caught by moving the pin and reading what the constant said
  rather than trusting that it still applied.
- **Two conformance rows were asserting a property of the empty set.** C19 and C20 ran against
  the *real* record to check that a stable release is refused while a round is open. Round 7
  closing left them with nothing open to refuse. They now run against a fixture — which is
  exactly what the previous author left in the failure message for this moment: *"re-point it
  at a fixture if the record has closed."* A companion row asserts the other half against the
  real record: the gate says **yes**, which is a fact about the project and not about a
  fixture. `scripts/handshake.py` grew `--handshake-dir` to make that testable, exposing a
  root `round_status()` already accepted.

### Fixed
- **The auto-fix addendum claimed a re-read "improved" the audio when it had confirmed it.**
  One unconditional sentence — *"the improved read was swapped in"* — in an archival record.
  On the J1 rip it was false: track 5 was re-ripped at `-Z 2`, converged after 5 reads, and
  came back with CRC32 `6902BCF0` — the value the album log already held at line 396. Nothing
  improved; the re-read **reproduced** the first pass, which is a better result and a
  different claim. Found by the cyanrip fork, confirmed here against the artifact rather than
  accepted on their word.

  Each track now carries its own **tri-state** outcome, derived from the two CRCs:
  `CONFIRMED`, `REPLACED` (naming the superseded CRC, so the claim is checkable), or
  `NOT DETERMINED` when either value is missing — never rounded to a positive answer. The
  text also says plainly that a confirmed read is a *good* outcome, because "not improved"
  reads as a failure to anyone who does not already know.
- **`HANDSHAKE-SOURCE-ANCHOR` was a copy of our own `seam-commands` hash.** Every lap that
  declared it carried `sha256/16 = 7dc313815850eb60`, which is character-for-character the
  first 16 hex of the `seam-commands` hash printed two lines below it in the same header. The
  field's entire purpose is to pin **our** source by content; it pinned a file **neither
  project owns**, so a `file:line` citation from any of our laps was checkable against
  nothing.

  Fixed at the mechanism, not the value: it is computed now
  (`scripts/handshake.py::source_anchor`, hashing `path\0content\0` across the seven files
  our half of the seam is made of, so a rename counts as a change), and a test refuses any
  lap whose declared anchor equals **any** shared file's prefix — not just that one, which
  would pass again the moment the shared file changed. The lesson is general: *a field whose
  value is typed by hand next to a similar-looking value will eventually be the other one.*

### Changed
- **Adopted the cyanrip fork's convergence rules (S-13 … S-16 + pre-commit) into `CLAUDE.md`.**
  Round 7 took 37 laps, 10 test pins and 8 pre-releases to produce 0 releases; rounds 5 and 6
  took one lap each. None of round 7's findings made the reviewed pin unsafe, and every one
  of them blocked it, because nothing ever asked whether it should. The rules fix the four
  mechanisms: close conditions are fixed at lap 1 (S-13); a finding defaults to the next round
  unless it names what it breaks in the artifact under review (S-14); an agreed test pin does
  not move (S-15); questions carry `BLOCKING`/`NEXT-ROUND` and a questions section may be
  empty (S-16); and a lap may pre-commit its next verdict. *Release-grade rigour was being
  applied to the round rather than to the release.*
- **The rig sheet no longer asks for a `-Z`-on-every-track rip.** It was going to cost ~80
  minutes to test whether per-track paranoia counters sum to the disc totals under `-Z`. The
  J1 rip already answered it: the album pass (no `-Z`, 14 tracks) sums exactly — READ
  21972 = 21972, all four counters — and the refix pass (`-Z 2 -l 5`, **one** track, so no
  summation ambiguity) does not: per-track READ **1538** against a disc total of **7738**,
  a ratio of 5.03 against a track that converged after 5 reads. **The invariant does not hold
  under `-Z`**, and a disc-level tally rendered as a count of distinct events over-reports by
  roughly the re-read count.

  Recorded as a correction in both directions: the fork asked us not to spend the session
  because the test *"cannot fail"*. Same action, opposite reason — it already had, in the
  artifact they were holding.


## [0.6.4b15] — 2026-08-06

### Added
- **Every rip now says what it is about to do, before it does it.** A `[plan]` block goes to
  the log *and* the on-screen live log as the first thing a rip emits, naming every cyanrip
  flag the settings become — and, where a setting has two modes hiding inside one on/off, which
  mode. The maintainer's ask, verbatim: *"the app builds the argv, so `-j` and `-Z` are its
  call — worth checking they're on before you start rather than discovering afterwards."*

  Until now the only record of what a rip ran was the finished artifact: `Invoked as:` in
  cyanrip's log, `ripper_argv` in our JSON. Both are post-mortem, which is the wrong end of a
  70-minute rip. The concrete case is not a bug and is genuinely surprising: **`-Z` is on by
  default at 2, and runs in *dynamic* mode by default** — pass 1 reads the whole disc with **no
  `-Z` at all**, and only tracks that miss AccurateRip are re-read with it. On a disc that fully
  matches AccurateRip, `-Z` is never applied. Settings said "on"; nothing said which "on".
  The plan now spells it out and names the checkbox that changes it.

  It also states the two flags we **never** send — `-j` and `-x` — positively, because "absent
  from the plan" and "we never send it" look identical to a reader. `rip_plan.py` is a pure
  function and deliberately **not** a second argv builder: it describes the *inputs* to the one
  builder plus the one decision the worker makes above it, so the plan and the artifact are two
  independent records of the same choice and a disagreement between them is a finding.
- **Tools → Run test script… — the batch console the scripting subsystem never had.** The
  `uiscript` package (parser, closed vocabulary, `QTimer` runner, transcript renderer, its own
  test file) shipped in b12 **entirely unwired**: no menu item, no dialog, no CLI flag. `grep`
  for the package anywhere outside itself returned nothing. So the maintainer's own ask — *"give
  me a debug testing option where i can copy and paste command code into it so i dont need to be
  present but tests get executed anyway in my absense"* — existed as a library nobody could
  invoke, with a changelog entry announcing it. That is `docs/testing.md` §5.p (*a documented
  capability is not a capability*) for the second time, and the fix is a surface, not behaviour.
- **A saved test script, and an option to run it at launch** (Settings → *Test script* /
  *Run it automatically when Platterpus starts*). A path rather than a text box, because a batch
  meant to run in your absence outlives one paste into one dialog — it is editable in your own
  editor and re-read on every run. Both the path and the autorun flag must be set deliberately;
  neither does anything alone. `--run-script FILE` does the same for a single launch. The path
  is validated where it is typed (exists, is a file, is readable), because a silently-missing
  script produces a launch indistinguishable from one where every test passed.
- **`--rig-session FOLDER` — the unattended hardware harness, reachable from the AppImage.** The
  harness itself is unchanged; where it lived was the bug. It sat in `scripts/`, which exists
  only in the git repository, while the person who runs it has an AppImage — and the rig sheet's
  instruction was literally `bash ~/path/to/Platterpus/scripts/rig_session.sh ~/rig-b11`, a
  placeholder path in a copy-pasteable block. It now ships inside the package (declared as
  package data, with a test that reads `pyproject.toml` to prove it, because a file present in a
  checkout and absent from the wheel is exactly the failure mode). Fourteen steps, one artifact
  each, never stopping on a failure — including the fork's `-x` and `-j`, the only place those
  records come from since a rip never sends either.

### Fixed
- **The Live log pane showed the past while the status line showed the present.** Real-user
  report, mid-rip: *"its odd it says its re-ripping track 5, but log says track 12."* The
  status read `Re-ripping track 5 to secure it… 97%`; the pane's visible lines read
  `Ripping and encoding track 12, progress - 7.22%`.

  Both halves are timestamped in the rip's own debug stream, so the staleness is measured
  rather than argued: the status matched `19:21:20,084 Ripping track 5, progress - 96.39%`,
  while the pane's visible tail was emitted at `18:59:35,904 … 18:59:36,434`. **The pane was
  21 minutes 44 seconds behind.**

  Measured cause: `QPlainTextEdit.appendPlainText` only auto-scrolls a widget Qt is actually
  laying out. In a **non-current tab** — where this view sits for most of a rip, because the
  user is watching the track grid — 400 appends leave the scrollbar at `value=0` against
  `maximum=399`. The content is all there; the viewport never moves, and whatever is on
  screen when you open the tab is whatever Qt's deferred layout restores. The pane now
  follows the tail itself, and re-pins when its tab becomes current; scrolling up still
  pauses the follow (it is a console — reading back is the point) and returning to the
  bottom resumes it.

  **The first version of the regression test passed against the broken code** and was
  rewritten: it asserted the position *after* switching tabs, where Qt happens to land at or
  one line short of the bottom depending on how lines wrap. The state that actually
  distinguishes the two implementations is the one *while the tab is hidden*, which is also
  the state that matters. Both halves of the fix are now revert-proven.
- **A release gate was choosing its subject by directory iteration order.**
  `test_the_pin_is_the_one_the_newest_closed_handshake_round_verified` is the guard that
  stops the setup wizard building a cyanrip commit no closed handshake round approved. Its
  name says *the newest CLOSED round*; its body took the last element of a sort keyed on the
  round number alone. Every `round-07-lap-NN.md` shares that key, Python's sort is stable, and
  the tie fell to **whatever the filesystem yielded last** — so the guard had been naming the
  right commit by luck for eight laps. Adding a ninth changed the answer and CI went red,
  which is the only reason anyone looked.

  Two fixes. It now orders with the **shared** `sort_key` (`(round, lap, stem)` — total by
  construction, the single definition both projects agreed on), and it asks the question its
  name asks: `FORK_PIN` is the *production* pin, approved by a **closed** round, so an open
  round's laps are not eligible to stand in for an approval. A companion test pins that
  subject explicitly, because otherwise the check could drift back to "newest file of any
  round" and still pass on days when the two agree.
- **The scripted `cyanrip` verb no longer freezes the window for up to five minutes.** It ran
  `run_capture` inline on the GUI thread with a 300-second timeout, and justified the block in
  its own docstring as acceptable *"here specifically"* — the shape `CLAUDE.md` refuses (*a
  comment where a check belongs is not a fix*). It is the same call with the same arguments,
  now on a daemon thread the tick polls; `stop()` kills an in-flight child rather than
  forgetting it, and a child that cannot be reaped is reported as such (exit code `null`, never
  `0`) instead of stranding the batch. Proven by revert: the two tests that assert the tick
  returns while the command is still running, and that a never-returning command is reported
  rather than waited on, both fail against the inline version.

### Changed
- **The fork's round-7 lap 33 and its beta.8 golden reference are filed.** Taken from their
  repository at `104f6d4` rather than from an upload — same file, better provenance, and the
  commit it came from is recorded. Their reference parses cleanly through our production parser
  (3 tracks, all `ripped successfully`, every copy CRC present, generating build read as
  `platterpus-fork-g92ceeed`). Their lap asks nothing new; it reports a source-tarball build that
  could not name itself, now fixed, and a version gate they added to their own golden reference
  after finding it had none.


## [0.6.4b14] — 2026-08-06

### Changed
- **`--install-ripper` and the setup wizard now build cyanrip `beta.8` (`104f6d4`), not `beta.5`.**
  This is the reason the release exists: the released b13 pinned `9048082` (beta.5), so a user
  updating and running the installer would have got the build the fork **withdrew** — the one whose
  `-t` parse reads past the end of a string and *publishes what it read* (an environment variable
  into a FLAC tag, the log and the cue, at exit 0). Platterpus can never emit the argument shape
  that triggers it, so this is about the **artifact**, not the app: a rip made on a withdrawn build
  is evidence you then have to argue about.

  The pin moved three times in an hour (`4a35604` → `92ceeed` → `104f6d4`), the first two reported
  out of band rather than in a handshake lap. Each was verified in the fork's own repository before
  being taken, and the check that mattered is that **`git diff 4a35604..104f6d4 -- 'src/*.c'
  'src/*.h'` is empty** — the ripping code is identical to the build both sides declared in
  writing. Their own source anchor is unchanged across the range, which is an independent witness,
  since that anchor is defined as a hash over exactly those files.

  Our own guard caught the gap rather than a person noticing: the wizard's target must be named in
  the handshake record, and it was not. Round 7 lap 34 declares it and asks the fork to confirm.

### Changed
- **The argv probe grew a malformed-shape axis, and it found three defects in itself before
  finding none in the argv.** The cyanrip fork added the same axis to their probe and it found
  **four segfaults on its first run**; their statement of why is the one worth keeping — *a grid
  that only feeds well-formed values has the same blind spot as a type signature.* Ours had
  varied numeric values on four flags and nothing else, so every metadata blob it had ever built
  was well-formed.

  Adding twelve structurally awkward values (`:`, `=`, `::`, `a:=b`, a trailing backslash, an
  unescaped separator) through the production path found, in order: an **expectation that was
  backwards**, reporting 12 defects against rows where the escaping had worked perfectly — a
  probe with a wrong expectation is worse than a missing one, because someone will change the
  code to satisfy it; a **blob selector** that reported the album value for three track-level
  rows; and an **outcome class nothing counted**, which made the experiment meant to prove the
  axis work pass with zero findings against a build with the escape deleted.

  The last one is the general fix. A finding is now **the complement of the pass** rather than a
  list of failures — an enumeration is only as complete as the imagination that wrote it — and
  the summary **reconciles**, naming any rows the classes do not account for. Our own line read
  "12 probes, 4 round-tripped, 0 mangled, 0 wrongly refused. Findings: 0" and 4+0+0 ≠ 12.

- **A generated section of a shared file was stale, and nothing checked it.** `docs/seam-commands.md`
  §1a carries `<!-- GENERATED … do not hand-edit -->` and is produced by the argv probe — so when
  the probe grew the shape axis, the committed table still claimed `26 probes` while the probe
  emitted 38. A do-not-hand-edit marker is a request; a regeneration diff is a check. Regenerated,
  and a test now regenerates and compares. It matters more than an ordinary stale doc because this
  file is shared with the cyanrip fork, so our stale claim was sitting in their tree too.

- **The shared seam files no longer carry a Platterpus version stamp.** `*Last updated for
  Platterpus vX*` inside a document whose entire purpose is being byte-identical in two
  repositories broke the hash on every beta, by construction. Our own stamp-exemption test
  already carried the argument — *"stamping it with our version would fork the one file whose
  entire purpose is not being forked"* — and enumerated one file while the reasoning covered
  three. The fork's evidence was the clean kind: the two files with the footer were exactly the
  two that drifted, and the footerless one matched first try.

- **Round 7 laps 32 and 33 filed.** Test pin moves to `4a35604` (beta.7) and **beta.6 is
  withdrawn** — the `-t` bounds defect we reported turned out to *publish* what it read past the
  string, putting an environment variable into a FLAC tag, the log and the cue at exit 0. Their
  three new refusal messages were checked against our surfacing matcher (3 of 3 matched, with a
  no-false-positive floor) and their beta.7 golden reference through our parser.

### Fixed
- **The changelog claimed a release that never existed.** `0.6.4b12` had a dated heading and a
  compare link, but no `v0.6.4b12` tag or GitHub release was ever cut — the version was bumped to
  b13 before the release went out, so b12's entries shipped *inside* b13. The link resolved to
  nothing and the b13 link pointed at it. Folded into b13 with a note saying so; entries kept
  verbatim. Three older headings (`0.5.16`, `0.2.0`, `0.0.1`) have the same defect and are
  **left alone pending a decision** — they predate this cycle and "fixing" a heading whose
  history we do not know would be a guess. Recorded in `TASKS.md` rather than silently kept.


## [0.6.4b13] — 2026-08-06

### Changed
- **The rig sheet carries the next rip's acceptance criteria, before the rip rather than after.** Four
  checks with a copy-pasteable command each: 14 ISRCs in the cue, `INDEX 00` on exactly
  2/4/5/7/8/9/10/13/14 **and nowhere else**, the `Offset:` line unchanged as the negative control for
  the fork's new argument bound, and the album title carrying a real colon in both the cue and the
  ripper's log. Each row states how it could pass for the wrong reason — a marker *count* of nine
  passes on the wrong nine, and beta.1 wrote thirteen markers of which four were for pre-gaps its own
  log measured at zero. The commands were verified against the committed reference cue, which
  reproduces beta.1's numbers exactly.

  Written because lap 31 told the fork these were already in our hardware sheet and they were not —
  the sheet held the beta.5 *analysis*, not the beta.6 *criteria*. Caught by re-reading our own sent
  claim rather than by anyone asking.

- **Round 7 lap 31 filed, and the fork's lap 30 correction accepted into the record.** Our
  lap 29 blamed the cue's ISRC regression on the fork; the branch is **upstream's**, and what
  the fork changed is only its *reachability*. Verified in their repository rather than taken
  on trust — a finding that arrives as "you got this wrong" is not pre-verified, and this
  project's own rule says a correction should not get *less* scrutiny than a claim. It is the
  third time a seam failure has turned out to be upstream's inherited by the fork, and the
  rule warning about exactly that was already written down here from the previous two.
- **The shared handshake protocol is back in sync with the cyanrip fork, and our copy was
  the stale one.** `docs/handshake-protocol.md` is a document *neither project owns* — the
  same file in both repositories — and ours had not been edited since the day it was adopted
  (round 7 lap 4), while theirs had absorbed three later laps. Established from evidence, not
  from argument: `git log` shows exactly one commit touching our copy, and the diff against
  theirs contains **§6b, a mechanism Platterpus itself proposed in lap 7** and never wrote
  into the shared file. Adopted verbatim, byte-identical.

  It brings three things: the round-8 requirement that every file name its own pair (on a
  mid-round `HOLD` too — a measurement without provenance is what the fields exist to
  prevent), the optional `HANDSHAKE-TEST-PIN`, and a conformance table with **stable row IDs
  `C1`–`C20`** so a disagreement can cite a row rather than a paraphrase.

  `HANDSHAKE-TEST-PIN` resolves a real deadlock: closing a round requires evidence that can
  only be gathered by installing the build under review, but neither side may move the pin
  while a round is open — so the test rig forever runs the build *without* the changes, and
  the round can never close. Our gate now enforces that a test pin is inert on a `HOLD` and
  can never stand in for the agreed pin.

  Our conformance suite is one test per row ID, with the **expected ID set parsed out of the
  shared table** rather than hardcoded. The version it replaced looped over a number range
  and skipped two entries, which had let two different tests both be named for "row 9" —
  either could have been deleted with the coverage check still green.

  One finding worth stating because it cuts against us: removing our local annotation from
  the top of the shared file broke a test that claimed to assert the *shared spec* says it is
  shared. It had been matching **our own comment** — the spec's own sentence is wrapped
  across a newline and never matched. A Platterpus-only comment inside a file whose entire
  purpose is byte-identity was itself the drift that file exists to prevent.

### Fixed
- **A colon in an album or track title is now sent to cyanrip as `\:` instead of being
  replaced by a lookalike character.** Titles with a colon — "Every Breath You Take: The
  Classics" — reached cyanrip's `-a`/`-t` arguments as U+2236 RATIO, a visually identical
  stand-in, because that parser could not then be trusted with an escaped colon. We repaired
  the FLAC tags and our own log afterwards, but **two artifacts we do not write kept the
  wrong character forever**: cyanrip's `.cue` `TITLE` line and its own log's `album:` field.
  Now the real colon goes in and comes back out, and nothing needs repairing. Folder names
  are unchanged — cyanrip still substitutes the lookalike when sanitising a *path*, which is
  where the character came from in the first place.

  What changed is cyanrip's code, not our opinion of it, and we verified that instead of
  taking the fork's word for it: its pre-splitter is now escape-aware **in both the fork and
  upstream**, present at the build installed on the test rig. Measured end-to-end where we
  could — the real function compiled out of the pinned tree against the real FFmpeg library —
  which also surfaced the finding below. Full confirmation that the escape survives into
  cyanrip's own written tags needs a rip on real hardware, so the post-rip repair pass stays
  armed as a safety net until then rather than being removed in the same release.

- **An unescaped separator in a tag value is refused at the argv chokepoint.** Measured
  against cyanrip's real parser, an unescaped `:` in a value does not fail — it **silently
  truncates**: `album=Every Breath You Take: The Classics` parses to `Every Breath You Take`,
  exit code 0, nothing in any log. The escape was correct at all twelve places that build a
  tag pair, but that is a rule enforced by everyone remembering it, and a thirteenth would
  have lost the user's text with no diagnostic. The blob's structure is now validated where
  every route to the ripper already passes.

- **The cue's titles are compared against the text we sent, not merely scanned for the old
  workaround.** The check that read the shipped `.cue` could previously only *pass by finding
  nothing* — and it was blind to the truncation above, which leaves no trace in the file.
  It now compares each title against the argv, so substitution, truncation and any other
  mangling are caught by one assertion, and reports **not determined** when there is nothing
  to compare against. A title containing a character a cue cannot quote is likewise not
  determined rather than accused.

- **The argv writer and the report reader can no longer disagree about the escaping.** They
  did, for the length of one change: the escape shipped on the write side while the read side
  still split naively, which turned the album title back into `Every Breath You Take\` and
  would have made the new title check accuse **every correct rip** of a disc whose title
  contains a colon. Both sides now share one implementation of cyanrip's blob syntax.

### Also in this release: everything prepared as 0.6.4b12, which was never tagged

The version was bumped to `0.6.4b13` before any release was cut, because the colon-escape
work landed after these entries were written. **No `v0.6.4b12` tag or GitHub release exists**,
so this is not a separate release and its compare link has been removed rather than left
pointing at a tag that resolves to nothing. The entries are kept verbatim: they describe
changes that shipped, in this release.

### Added
- **The `.cue` cyanrip writes is now validated before we ship it** (`cue_validate.py`,
  a new `cue_integrity` self-check). The cue was **external input nobody read** — the
  2026-08-05 rig rip handed the user a cue missing **9 of its 14 ISRCs** and carrying a
  U+2236 escaping artefact in the album title, and *both were derivable from facts already
  in the report*. The validator judges the cue against what we know **independently** of it:
  the ISRCs and titles from the argv we sent, the pre-gap frame counts from the ripper's own
  log. Checking an artifact against itself is consistent, not verified.

  Every check is tri-state — an absent, empty or truncated cue is *not determined*, never a
  pass — and the one false positive that would make the validator worse than nothing is
  explicitly excluded: a U+2236 inside a `FILE` line is **correct** and never flagged, because
  that character really is in the filename on disk.

### Changed
- **Documentation consolidated: 27 top-level docs → 22, and a rule so it stops growing.**
  The maintainer's instruction was blunt — *"make sure you are not making and adding md files
  just for the sake of it … amalgamate as much as you can into the fewest files possible
  without losing info and context"* — and it was earned: **four** new docs appeared inside
  **71 minutes** on 2026-08-06, one of which lived **43 minutes** before being deleted, and
  five separate rig sheets accumulated in three days for one recurring activity.

  Merged: the release plan into `TASKS.md` (which is the declared home for a task queue), the
  error-reporting design into `docs/architecture.md` beside the error-handling rules it
  restated, AppImage testing and the release-signing ritual into that file's packaging
  section, and the shipped multi-format design-of-record into `docs/archive/` — with its one
  still-open item graduated to `TASKS.md` first, because archiving a doc with a live item
  loses it.

  **Critical rule #7 gained a fourth obligation:** a durable lesson graduates into an
  *existing* home; a **new** document requires that no existing home fits, and the commit must
  name the homes considered and why each failed. A recurring activity's sheet is **rewritten**
  when it goes stale, never joined by a sibling.

  Two carve-outs, because they cut the other way: the handshake correspondence is
  **append-only** (a merged round file is a falsified record), and the EAC-compatible log
  stays as close to EAC's original as it can get without forging — consolidation applies to
  *documentation*, never to *evidence*.

- **A doc CLAUDE.md merely mentions can no longer vanish unnoticed.** `CLAUDE.md` names some
  docs in plain backticks rather than as links, and the companion-list check filtered its
  candidates to files that *still exist* — so deleting a doc CLAUDE.md mentions left a stale
  reference no test could see. Now every `docs/<name>.md` string anywhere in `CLAUDE.md` must
  resolve, with a floor so the check cannot pass by finding nothing.

- **Handshake round 7 lap 29 sent, with a HOLD on pin `9048082`.** Verified from the rig
  artifacts: the fork's `INDEX 00` pre-gap markers are **correct on all nine tracks** — the
  same nine EAC marks on this disc, and each resolving to the sector against the pre-gap start
  LSN in the ripper's own log. Held anyway, because the commit that added them stopped writing
  `ISRC`: the cue carries 5 of 14, and the missing nine are *exactly* the nine with a marker.
  Proven across two fork builds by a relation that holds in both (surviving ISRCs = 14 −
  marker count), with stock cyanrip (14 ISRCs, 0 markers) and EAC (14 and 9 together) as
  controls. Lap 27's stale HOLD is withdrawn separately — its stated reason, the missing flag
  table, is satisfied.

- **The auto-fix supersede can now also be rebuilt from the JSON report**, so a folder
  whose sidecar is missing — one written by an older build, or one where the write failed —
  still resolves a re-ripped track to the values actually on disk instead of the discarded
  pass's.

  **The sidecar file itself stays**, and the attempt to retire it is worth recording
  because it failed for a reason a file count does not outweigh: the post-rip finish
  handler re-parses the ripper's log *before* `write_report` runs, so at that moment there
  is no report to read and removing the file made that re-parse return the **discarded**
  CRC — reintroducing the precise defect the addendum exists to prevent. An existing test
  caught it. The per-rip folder therefore still carries the sidecar, and only when a track
  was genuinely swapped.

- **Every rip now records a retag-surviving audio identity** (`audio_md5`, schema v24).
  The existing `checksums` map digests the **container**, so writing a tag rewrites the file
  and invalidates the SHA-256 while the audio is untouched — a retagged album looked exactly
  as suspect as a corrupted one. Every FLAC already carries an MD5 of its decoded samples in
  `STREAMINFO`; we simply were not reading it, and EAC records nothing comparable.

  Parsed in pure Python (42 header bytes per file) rather than shelling out to
  `metaflac --show-md5sum`, so the field cannot go missing because a tool is absent.
  Verified against the rig's own `metaflac` output on the reference disc — same value,
  byte for byte. Tri-state: a non-FLAC, a truncated file, or the spec's all-zero
  "not computed" value yields **no key**, never a fabricated digest that every silent
  file would match.

  Kept as its own key rather than folded into `checksums`, because a SHA-256 mismatch
  after a retag is *expected* while an audio-MD5 mismatch never is, and the two must not
  be confusable. This is also what removes the need for the hand-collected rig-evidence
  sidecar: the report now carries what that file was carrying.

- **Out-of-range values could reach the ripper, and a black-box self-probe found it.**
  `docs/seam-rules.md` S-9 asks each side to establish its own limits by *probing its own
  surface*, so `scripts/probe_argv_surface.py` now does that for the argv builder and the
  chokepoint — both pure functions, so the whole grid (below-min / min / typical / max /
  one-past) runs with no drive and no disc.

  On its first run it measured **six unvalidated values reaching the argv**: `-r -1`,
  `-r 2147483648`, `-S 999`, `-S 2147483648`, `-s 2147483648` and `-Z 1000`. Every one was
  outside the range the Settings dialog already enforces, and every one was reachable
  **because the range was checked at the Settings boundary and nowhere else** — so a
  hand-edited `config.toml`, or any caller that skips Settings, handed it straight to a C
  program. CLAUDE.md says range "must be enforced by code at the argv chokepoint — not
  merely stated here"; it was stated and not enforced.

  All six are refused now, at the chokepoint, reusing the *same* constants
  `settings_validation` defines so the dialog and the argv cannot disagree about what is
  acceptable. Each refusal names the flag, the value and the range — `usable` under S-12,
  not the `generic` grade the rules call a defect in its own right.

  Two more were **silently dropped**: `-S -1` and `-Z -1` emitted no flag and no complaint,
  because `0` means "auto" and a negative fell through the same branch. A caller that
  computed a negative got a default that looked deliberate. Also refused now.

  The probe is a **gate, not a report**: one test fails if any non-zero value a caller set
  vanishes without a refusal, and a second fails if *nothing* is ever refused — which would
  mean the guard had been removed and the first test would still pass.

- **`docs/seam-commands.md` gained a return-path section.** The table had an outbound half
  and no inbound half, which is precisely why the cue was ungoverned. Every artifact the
  ripper hands back now has a row with its type, what it must satisfy, and the test that
  asserts it.

### Fixed
- **The rip ETA froze instead of exploding.** During the post-rip auto-fix pass the estimate
  sat at **2580 s for 47 consecutive samples**, and the last one read *"about 43m 0s left"*
  with **four seconds** to go — while cyanrip's own estimate said `3s` and was right. The b8
  fix for an ETA *explosion* had created a *freeze*: it held the stale **album** estimate
  through a phase that is one track long.

  The two cases are now distinguished **structurally**, not heuristically — the auto-fix pass
  is a separate invocation with `-l <track>`, so the worker is told which kind of pass it is
  rather than inferring it from a clock going backwards. A securing pass gets its own rate
  window, its own estimate scoped to the read it is actually measuring, and wording that
  never implies it knows how many more re-reads there will be. The album-pass re-read hold —
  the b8 fix — is unchanged and separately pinned, because removing it would restore the
  explosion.

- **The album progress bar ran backwards.** The same pass rewound it from **94.77% → 35.45%**
  and relabelled itself *"Ripping track 5 of 14…"* after all 14 tracks were already on disk,
  with a 99% track-local figure in the same sentence as the 35.45% bar.

- **`scripts/handshake.py --check` never validated our own outbound files.**
  `check_outbound` existed, was correct, and **had no caller** — the CLI ran the *inbound*
  spec against everything, so checking one of our own round files reported six sections
  "missing" that the outbound spec never asks for, plus a wrong-sender complaint. Seven bogus
  problems on a correct file is how a checker gets switched off. `--check` now routes by
  direction (outbound / inbound / verification), and each checker has a test proving it can
  **fail**. Same shape as the `RipHandle.cancel` that was fully implemented and called from
  nowhere: grep for a call site before believing a capability is reachable.


### Added
- **In-app UI scripting (in progress) — the pure layer.** A closed-vocabulary batch language
  so hardware tests can run unattended: paste a script, run it, paste the transcript back.
  Landed so far: the vocabulary (`uiscript/verbs.py`), the parser (`uiscript/script.py`) and
  the transcript (`uiscript/report.py`), with 29 tests. The runner and console follow.

  Design commitments, each protecting against something specific: the vocabulary is **closed**
  (no "click any widget", no destructive verbs — an unattended `eject` or `uninstall` has an
  unbounded failure mode); the escape hatch the maintainer asked for exists as exactly two
  verbs (`eval`, `call`) behind a **separate** opt-in, and a run that used them says so at the
  top of its own transcript; and **a failing step never stops the batch**, the same rule as
  `scripts/rig_session.sh` — a failing step is data, and an unattended run that halts on its
  first surprise wastes the session.

  The parser never raises, because a script is external input and a traceback on line 12 of a
  60-line batch destroys the other 59 results. Its sharpest edge is already pinned: a `#`
  inside a quoted value is **not** a comment, because album titles contain one and setting
  album titles is precisely what this language is for — a naive split would truncate the value
  silently and the transcript would agree with itself.


### Fixed
- **The Settings dialog could not be made short enough to fit the screen, so OK and Cancel
  fell off the bottom.** Its `minimumSizeHint` was **739 × 971** — a `QFormLayout`'s minimum
  is the sum of its 35 rows, so *no* resize could help, and the b11 labels widened it enough
  to start clipping horizontally too. `CenteredDialog` could not rescue it: it clamps a
  dialog's *position* onto the screen and deliberately never resizes it. The form now lives in
  a `QScrollArea`, which drops the floor to **146 px**; the validation banner, *Check
  dependencies* and OK/Cancel stay **outside** it, because an error message or an OK button
  that can scroll out of view is the same bug one level down. The dialog also opens clamped to
  the usable screen instead of to its own size hint.

  The trap this set, pinned by its own test: a `QScrollArea` reports a small arbitrary hint
  *by design*, so sizing the dialog from `self.sizeHint()` opened it at 526 × 414 showing a
  third of the form — the complaint inverted rather than fixed. The opening size is measured
  off the inner form plus the chrome deliberately kept outside it.


## [0.6.4b11] — 2026-08-06

### Changed
- **Every option in every Settings dropdown now follows one naming convention** —
  `Name — Descriptor In Title Case [Qualifier]` — instead of the five different
  phrasings that had accumulated across five combos in one dialog (an em dash here, a
  lowercase parenthetical there, a bare `Embed in FLAC` with no description at all, and
  two labels using the same round bracket for two different jobs). The maintainer read
  that dialog on the rig and asked for it, giving the syntax by example:
  *"Flack - Lossless Archival Master [Debugging] or similar, and other settings should
  reflect similar naming syntax."* So `FLAC — Lossless Archival Master [Recommended]`,
  `Adaptive Ladder — Fast, Slower Only if a Disc Needs It [Recommended]`,
  `Embed and Save File — Both [Recommended]`, `Custom — Hand-Tuned Below`.

  The convention lives in one new module (`option_labels.py`) **with a checker**, not as a
  style note: `check_option_label()` is pure, and the test sweeps *every item of every
  combo in the constructed dialog* rather than a table of the labels we happen to know
  about — so a dropdown added next year is covered without anyone remembering the rule.
  This project's own lesson, twice recorded: *a comment where a check belongs is not a
  fix*, and *enforce a rule across the codebase, not at the place it was learned*. The
  checker is pinned non-vacuous by a test asserting all **19** pre-rename labels fail it,
  and a second test asserting every combo still carries the same item **data**, because a
  relabel that quietly reordered a value would change behaviour while reading as a copy
  edit. `naming.CUSTOM_LABEL` is now one shared constant instead of a literal duplicated
  four hundred lines away in the same dialog.

### Fixed
- **The dependency dialog said `cyanrip 0.9.4 (the Platterpus fork)` for a binary whose own
  banner reads `cyanrip 0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)`** — every
  word accurate, the message wrong, and the *captured-and-discarded* kind: both the full
  banner and the build tag were already in the object that dialog receives. Two independent
  losses met there: `parse_version` reduces a version to an int triple, so
  `-rc1+platterpus.5-beta.5` is structurally unrepresentable, and the build was collapsed to
  a four-word phrase. `BuildNote` now carries the tool's own version string and its build
  tag, and the row reads
  `cyanrip 0.9.4-rc1+platterpus.5-beta.5 (the Platterpus fork; build tag "platterpus-fork-g9048082")`.
  This is Critical rule #12's *say which build* obligation, previously met in the log, the
  JSON and `--doctor` but **not** on the one surface a user reads at launch.
- **The setup wizard's fork row named no commit either** — `✓ Platterpus fork of cyanrip
  (build + export) — already present`, while the probe deciding "already present" reads the
  target pin two lines above its own comparison. The row now reads
  `… — commit 9048082` with `already present — the installed banner names commit 9048082`,
  worded to match what the probe actually checked rather than claiming an equality nobody
  tested.
- **A modal dialog left no trace in the log, so "waiting for a human" and "wedged" were the
  same silence.** The maintainer closed the app mid-session because it *"looked hung"*; it
  was waiting on the MusicBrainz release picker with four candidates, and the log has a
  **96-second gap** because that path logged nothing on any branch — not opened, not
  waiting, not accepted, not cancelled. Every dialog now logs that it was *presented*
  (from `showEvent`, so the line is evidence Qt actually mapped the window, not merely that
  we asked) and how it closed, on the shared `CenteredDialog` base rather than only at the
  call site that was found wanting. The picker additionally logs the candidate count and
  says **"this is not a hang"** in words, plus how long the wait lasted and what came out of
  it. The mechanism first suspected — a modal swallowing the picker — is impossible and is
  recorded as refuted: MB results arrive as a queued cross-thread signal, which a nested Qt
  event loop still delivers.
- **A rip's permanent record could name a goal its own settings never matched.**
  `settings.rip_goal` was read back from `config.rip_goal`, which is only a *label* for a
  bundle of six fields with nothing keeping the two in step — a hand-edited `config.toml`, a
  field changed outside `apply_preset`, or a config written before the field existed all
  leave a stale label behind. The Settings dialog had always re-derived (so the screen was
  right, which is why this hid); the report now derives it the same way, via the same
  function, and keeps the stored value as `settings.rip_goal_stored` **only when the two
  disagree** — the disagreement is itself a finding, and discarding it silently would be the
  same bug in a smaller place. Report schema **v22 → v23**.
- **`DiagnosticsDialog` was the one dialog that subclassed `QDialog` directly**, so it
  inherited neither the centring nor the new lifecycle lines — a *diagnostics* window that
  left no trace of having been opened. Found by a sweep (`test_every_dialog_in_the_app_inherits_the_logging_base`,
  derived from the source with a floor of 15 scanned modules), not by memory, and the sweep
  is what stops the next one.
- **An unbounded `\s*` in the new label checker** backtracked super-linearly (16× the time
  for 4× the input, on a run of tabs). Found by `test_regex_bounded_time.py`, not by care —
  which is the point of having it.

### Documentation
- **The four superseded rig-session sheets are archived and replaced by one
  `docs/rig-session.md`.** Five near-duplicate sheets had accumulated, each written for one
  app-build/ripper-pin pairing, and the maintainer had already asked for the pile to be
  combined. One current sheet that names its pair in its header does the job; the dated ones
  move to `docs/archive/` where their audit trail is still readable.
- **`README.md` now says where the AppImage actually is** before handing out
  `./platterpus-x86_64.AppImage …` commands. Accepting the first-run "add to menu" offer
  **moves** the file to `~/Applications/`, so a `./`-relative command run from the download
  folder afterwards reports *No such file or directory* — correct behaviour that was already
  mistaken once for a bug, because the instruction was wrong and not the app. The same note
  is in `docs/test-plan.md` and `docs/hardware-test-checklist.md`.

## [0.6.4b10] — 2026-08-05

### Changed
- **The cyanrip test pin moves `f5e11ba` → `9048082`** (`beta.4` → `beta.5`), retiring
  `f5e11ba`. It is retired for a defect **our own rip found**, which is a first: on tracks
  3, 6, 11 and 12 the ripper's log says `Pregap length: 0 frames` and the cue writes an
  `INDEX 00` anyway, one frame past the end of the previous `FILE`. Present in all three cue
  sheets on record, so it is as old as the fork's sub-channel pre-gap search rather than a
  `beta.4` regression. The pin is the **artifacts** commit, not the version bump `c10cc94` —
  same ripping code, but `c10cc94`'s in-tree provider contract still describes `beta.4`
  (their generator reads the built binary and refuses on a dirty tree, so a contract can
  never be regenerated in the commit that bumps the version).

### Added
- **`--install-ripper` takes a commit**, which is what makes a rule we already wrote
  actually true. Critical rule #12 says *"a moving pin needs a route to it that does not ship
  inside a release"* and names this flag as that route — but it built a module constant, so
  reaching a new pin still required cutting a Platterpus release, exactly the granularity the
  rule calls wrong. The fork's pin has moved **five times inside one round**, twice in a
  single day. `--install-ripper 9048082` now builds that commit through the same step engine,
  and verifies the binary reports `platterpus-fork-g9048082`.

  It deliberately does **not** predict the version string for a commit we don't pin: we
  cannot read that tree's `meson.build`, and printing a guess beside the word "expects"
  invites a comparison against a number nobody measured. The build tag is checked, the
  version is declared unpredictable, and the non-approved status is stated *before* minutes
  of `dnf` and `meson` rather than left for the rip report to reveal. The target is resolved
  **once** and threaded to both the readiness check and the build — those two have already
  diverged in this codebase, which reported a correct install as "not done" and rebuilt it
  every run.

### Fixed
- **The argv-surface check was structurally blind, and the flag table arriving did not fix
  it on its own.** For the whole of round 7 every lap cited `PROVIDER-CONTRACT.md @ <commit>`
  in the *fork's* repository, which we did not hold — so
  `tests/test_argv_surface_agreement.py` diffed our argv against **round 6b's** table and
  said so out loud, which is the only reason anyone knew. Lap 25 shipped the contract as an
  attached artifact; archiving it changed nothing, because the round-grouping globbed only
  lap files and the shared round parser returns `None` for an artifact's name. **A contract
  sitting in a directory nothing reads is not a contract received.** Artifacts now resolve
  to their lap's round through the shared parser (one resolver, three call sites — two had
  already begun to diverge), so the check reads the round's own table: 82 flag spellings
  over 42 rows, and `_MAX_TABLE_LAG` ratchets `1 → 0`. Revert-proved twice — once with the
  artifact resolution removed, once with the contract itself absent — and both reproduce the
  silent fallback to round 6.

### Added
- **The input half of the cyanrip contract is checked against the current pin at last.**
  Every flag we send (`--verify-log --version -D -F -G -N -O -S -V -Z -a -c -d -l -o -r -s
  -t`) is accepted by `beta.5`, and beta.5's golden reference parses with **zero
  unrecognised lines** — including `Pregap LSN: 0` on a track-1 HTOA, which is the C1 case
  we had recorded as untestable and is exactly where a falsy-zero bug would hide.

## [0.6.4b9] — 2026-08-05

### Fixed
- **The archival log said "INCOMPLETE RIP (cancelled) — this log covers 14 of 14 disc
  tracks"** — asserting a gap and reporting none, in one sentence. It assumed any
  non-success outcome means an incomplete extraction, and the rig produces a shape where
  that is false: the whole-disc pass extracts every track and the *securing* pass
  afterwards is cancelled. Every track is present, so the banner now says **`RIP STOPPED
  (cancelled)`** and states that the extraction is complete while anything running after
  it may not be. A **truncated** log is deliberately excluded from that branch: there
  the track count is a floor rather than a total (the rig lost a track that had
  completed and matched AccurateRip at confidence 200 because cyanrip was killed with
  4 KiB unflushed), so "every track is present" is precisely the claim it cannot
  support. Found by the test written for the item below.
- **The log said the securing pass was `INTERRUPTED` without saying the user
  interrupted it** — while the app had that recorded. It now reads *"INTERRUPTED (you
  cancelled the rip)"* when the outcome was a cancel, and is unchanged when the pass was
  cut short by anything else, so a crash is never attributed to the user. Same shape as
  the cancelled rip that reported `"success"`: captured and not surfaced is the same bug
  from the reader's side, and this line was the *only* mention of it — the
  incomplete-rip banner correctly stays silent on a disc where every track is present.
- **The track list opened showing 2 rows of 14, and its columns moved on every track
  transition.** Both measured from the maintainer's screenshots (2026-08-05,
  *"make sure to keep formatting in mind too"*), and they are two separate defects:
  - **The columns would not sit still.** Every column but Title/Artist was on
    `ResizeToContents`, which re-measures whenever its data changes — and the Status
    column's data changes on *every* track transition. At a 900 px window: Status
    swung `48 → 67 → 53 px` as one track advanced, and the two stretch columns gave and
    took to absorb it, sliding the Title text sideways roughly **twice per track, 28
    times over a disc**. Now only Title stretches; every other column is sized once per
    *disc* from the widest string it can ever hold, derived from the same table the
    cells render from so a new status string widens the column on its own. Also fixes
    the other half: Title and Artist were both `Stretch`, which splits the remainder
    evenly, so a column repeating `"The Police"` (~70 px) was handed 369 px while the
    long, varied titles got the same. Title now gets 616 px against Artist's 77, and
    Artist is capped at a share of the table so a compilation's long credits still
    cannot crowd it out.
  - **The window opened too short, and the knob that looked responsible was inert.**
    The splitter handed the track list 169 of 647 px — 84 for the album form, 20 for
    the header, a 65 px viewport at a 30 px row height. The stretch factors are *not*
    what distributes here: measured at four different factor sets across four window
    sizes, every combination produced **byte-identical** pane sizes, because Qt
    distributes by factor only what is left after each pane's size hint and the rip
    pane's hint already claims it all. An explicit split on first show plus a taller
    default (clamped to the screen, so a 1366×768 laptop still gets a window that fits)
    takes it to **7 of 14 rows**, with the rip pane at 315 px against 326 before — the
    room comes from the taller window, not out of the other panes. The split is applied
    once, so it can never undo the user's own dragging; that is the fix's own new
    failure mode and it has its own test.
- **A secure re-read was reported as a scratched disc, and made the ETA climb to 5h40m
  on a disc with 22 minutes to go.** Two symptoms, one cause, both in the b8 rig
  artifacts (2026-08-05, the Police baseline disc). The rip's own debug log carries
  `rip stalled: no forward progress for 3m 2s at 21.7% (track 3) — the drive is stuck on
  a hard-to-read spot` **twice**, timestamped in the same seconds as
  `cyanrip │ Ripping track 3, progress - 52.29%` … `54.50%` — a steady 1× read of a
  disc with nothing wrong with it. The cause is that `_overall_from_track` maps a track's
  progress into a span of the album the bar has already covered and `_bump_overall`
  refuses to let it regress, so the **album fraction is pinned for the whole of a secure
  re-read** — ten minutes of it here. Watching only that fraction, a healthy converging
  re-read is indistinguishable from a wedged drive, and `(1 − 0.2173)` of an album
  divided by whatever noise is left in the window produced 54m → 1h5m → 1h50m → 3h15m →
  **5h40m across 70 seconds**. The divisor floor added for the 62-hour bug could not
  catch this one: for the first 90 s of the freeze the window still holds real
  pre-freeze movement, so the floor is legitimately met. Now: the stall detector takes a
  **second, independent liveness signal** — cyanrip's own per-operation percentage, which
  advances on a re-read as much as a first read — and reports "stalled" only when
  *neither* signal has moved, which makes it strictly more sensitive (a truly wedged
  drive stops printing progress lines at all, so both go quiet together). And while a
  re-read is running the estimate is **held and labelled** — `· verifying track 3
  (re-read 2) · about 54m left` — because the remaining album work genuinely has not
  changed and the cost of the re-read is unknowable until it converges. All four parts
  revert-proved; reverting the liveness signal reproduces the field warning text
  verbatim.
- **A rip the user cancelled was recorded as `"success"`.** Measured on real hardware,
  2026-08-05, and reported as *"I cancelled it early. It should be easy to tell that."*
  It was not — the report said the opposite. `success` and `_rip_cancelled` are **not
  mutually exclusive**, which `if success: … elif self._rip_cancelled:` assumed: the
  whole-disc pass completed all 14 tracks (so `success` was `True`) and the *securing*
  pass that runs afterwards was then cancelled. `success` won, and the report carried
  three mutually contradictory statements — `outcome.status = "success"`,
  `ripper_exit_code = 1` (non-zero, because it was killed), `failure_hint = null` — with
  the word "cancel" appearing **nowhere** outside the embedded debug log, even though the
  app log records it at INFO. Captured and never surfaced, which counts as the same bug
  from the user's side. The cancel is now checked first: a run the user stopped is a
  cancelled run even if every track happened to land, and `completeness` carries the good
  news separately (14 of 14 present). Revert-proved.
- **The re-rip comparison said *"can't tell which read is correct"* when it could tell.**
  Two rips of the same disc read track 5 differently, both offset-variant at confidence
  200 — identical status, identical confidence — so `_decide_better` gave up. But one read
  had **converged across three secure re-reads** and the other was a single read with
  `Secure re-read: not attempted`, and **EAC independently produced the converged one,
  twice.** Convergence is now the tiebreak after confidence: a read corroborated by
  repeating it on this drive beats one nobody checked. Ranked *below* confidence
  deliberately — confidence is corroboration by many independent rippers, convergence by
  one drive repeating itself — so it can never overturn an AccurateRip verdict, only
  replace a shrug. Tri-state throughout: "never re-read" is not "failed to converge", and
  with neither read corroborated it still returns `unknown` rather than inventing a
  preference.

### Added
- **Handshake round 7, lap 27 sent** (`docs/handshake/verified/round-07-lap-27.md`) —
  still a **HOLD on `f5e11ba`**, for one reason that is not about the fork's build: the
  P1 flag table for this pin has not arrived, so the *input* half of the contract cannot
  be checked and `tests/test_argv_surface_agreement.py` is still diffing our argv against
  round 6b's table. What the lap does carry: the fork's A2 change **verified at the
  drive, twice with different numbers** (`1/14` on b6, `2/14` on b8 — same disc, same
  build, so the field is genuinely counted rather than a string that happens to read
  `/14`, which one observation could not have shown); their A1 rewording present verbatim
  in three rig logs; `--verify-log` accepting all three; and our own §G2 claim
  **withdrawn** — the cover-art refusal sits 13 lines *below* the `Release ID:` header,
  settled from a log we hold rather than derived from either project's source, which is
  the pairing the fork's contract records as having no available artifact.
- **The report now records the release id the ripper *used*, and flags it when that
  disagrees with the one we sent.** `rip.ripper_release_id`, read off cyanrip's own
  header (schema v22). It had been in the parser's ignored table with a recorded reason
  — *"our own input reflected; `Invoked as:` is a better witness for an argv
  disagreement"* — which is true of the argv question and answers a different one. We
  hand the whole tag set as **one colon-delimited `-a` blob**, so what the ripper
  *received* and what it *parsed out of that blob* are separate claims, and only the
  first was recorded. The failure mode is live rather than theoretical: the reference
  disc's album title carries `∶` (U+2236, a lookalike) precisely because a real colon
  breaks that syntax, and a tag that split wrong would land in the wrong field silently.
  Two `issues` entries make the field more than a record — an `error` when the two ids
  differ (the tags, filenames and cue on disk may describe another release), and a
  `warning` when the ripper reports an id on a rip that sent none, which means `-N` did
  not suppress its own MusicBrainz lookup (Critical rule #5, now checked at the artifact
  instead of trusted). Tri-state: an absent echo is no claim, not a disagreement.
- **The auto-fix re-rip is now validated against an independent ripper, on the disc's
  worst track.** Track 5 of the EAC baseline disc was read **twice with different
  results** on 2026-08-04, so Platterpus discarded the first read and swapped in the
  second — the most consequential thing the auto-fix can do, and nothing in-house could
  check it (comparing cyanrip against cyanrip compares relatives; AccurateRip does not
  help because this pressing does not match its consensus at all). **EAC settles it:**
  the committed baseline holds two independent EAC 1.8 extractions of the same disc in
  the same drive, and both report for track 5 exactly the values our re-rip produced
  (`Test CRC E0036697`, `Copy CRC E0036697`, AR v2 `9EEB8843`), while the read we threw
  away (`6902BCF0` / `268CCD94`) appears in **neither**. `tests/test_track5_autofix_vs_eac.py`
  reads the committed artifacts rather than restating them, asserts both halves (EAC
  agrees with what we kept **and** does not contain what we discarded — agreement with
  both would be agreement with neither), and was adversarially checked by swapping the
  two constants, which fails it.
- **`output_reference/EAC_flac/eac_pcm_md5.txt`** — EAC's own decoded-PCM MD5s for five
  tracks. FLAC's STREAMINFO carries an MD5 of the *unencoded* audio, so equal MD5s prove
  **byte-identical PCM** — a direct proof where a CRC32 comparison is a proof about a
  32-bit digest, against an independent implementation rather than a relative, and it
  moves **only text** (critical rule #8). One command produces the comparable value:
  `metaflac --show-md5sum *.flac`.

### Fixed
- **A duplicate `(directory, round, lap, sender)` failed OPEN in the handshake gate.**
  The cyanrip fork revised and re-sent its round-7 lap-25 file — protocol §2 says a sent
  file is never edited — and keeping both copies created two files at one lap. `sort_key`
  is `(round, lap, stem)`, so the tie falls through to the **filename**: measured on the
  real pair, the *revision* sorted first, so the gate would have read the **superseded**
  file's verdict as the round's newest word. Both declared `HOLD`, so nothing broke —
  which is how this class of bug survives. `ordering_blockers` now refuses it, scoped per
  directory because an outbound round file and our verification of it can legitimately
  share a lap. This is the **third** fail-open ordering hole in that function's own
  subject matter. The earlier copy is preserved under
  `docs/handshake/inbound/superseded/` with a README explaining why — a subdirectory
  rather than a filename exception, because an exception threaded through three separate
  conformance checks is how a rule quietly stops applying.

### Changed
- Documented where the ETA's progress-delta floor actually bites: past roughly **12.5
  hours** of total rip time, a 90-second window's progress falls below `0.002` and the
  estimate is held rather than refreshed. Safe direction, real boundary, previously
  undocumented.

## [0.6.4b8] — 2026-08-05

**A double-check pass over `b7`, at the maintainer's request to re-verify *"especially what you think is correct"* — it found six real problems, five of them in work just called done.**

### Fixed
- **`artifacts` omitted the auto-fix addendum** — the one companion file that
  *supersedes* the ripper's log — while its own note promised *"this one file is enough
  to diagnose a rip without asking for the others"*. So for a re-ripped track the report
  embedded the **discarded** read's values verbatim and not the correction. Found by the
  maintainer asking why the addendum could not live in the JSON: a question about
  placement that turned out to be about absence.
- **The report's key order made a partial read useless.** JSON is order-preserving on the
  wire, and the measured order buried the decisive blocks: `self_check` — which says
  whether the report is *trustworthy* — sat at byte **1,515,002 of 1,516,421**, behind
  1.23 MB of `debug`, because it is assigned after the builder returns. `tracks`,
  `issues` and `checksums` all sat past byte 147,000. The decisive small blocks now come
  first and the three bulk blocks (`eta_trace`, `artifacts`, `debug`) last, so
  `head -c 4096` answers *did it work, what went wrong, is this report sound*. No key is
  added or removed — order only.
- **Three bugs in `scripts/rig_session.sh`, all found by running it rather than reading
  it**: the completion banner ended up *before* the steps added in b7, so the summary
  said `COMPLETE` with five steps still to run; `ls` on a glob matching nothing exits 2
  and `set -e` killed the script mid-step — in the script whose whole purpose is that a
  failing step is data; and the "not in a checkout" branch wrote one of its two
  artifacts, breaking the script's own "writes a file even when it finds nothing" rule.

### Added
- **`tests/test_rig_session_script.py`** — the script had **no** test. The b6 changelog
  described a *manual* run (*"smoke-tested with every binary absent"*) as though it were
  a standing check, and the script regressed the moment it grew a second half. A
  described verification is not a check.
- **Two ETA tests that were not discriminating are now revert-proved.** All four failed
  against a complete revert only after fixing them: one was measuring the pre-existing
  **stall detector** rather than the new hold path, and the field-trace replay passed
  with the bug restored because `eta_trace` rounds percentages to 2 dp — so the literal
  values give a delta of *exactly zero*, which even the buggy code handled. The
  explosion needed a delta *tiny but positive*, below the trace's own resolution. The
  replay now carries that wobble, marked as **inferred** rather than observed, and holds
  the freeze under the 180 s stall threshold — because the rip's own log shows
  `rip stalled: no forward progress for 3m 0s at 35.5%`, i.e. the bug lives in the
  window *before* the stall detector rescues the display.

## [0.6.4b7] — 2026-08-05

**Everything here came out of one real rip's own artifacts** — the 2026-08-05 Police
baseline rip on `b6` + cyanrip `f5e11ba`. The A2 denominator change landed correctly in
the field (`partially_accurate_reported: "1/14"`, sentence unchanged), and the report's
383-sample `eta_trace` was what made the timing bug measurable rather than anecdotal.

### Fixed
- **The album ETA could reach 62 hours on a 60-minute disc.** Measured from the rip's own
  trace: during track 5's auto-fix re-rip the estimate climbed `51 → 59 → 70 → 85 → 115 →
  175 → 335 → **3715 minutes**` across eight consecutive samples, then snapped back to 11
  — the maintainer's *"track 5 went from hours to minutes"*. **Cause:** the remaining time
  is projected as `(1 − frac) × window_dt ÷ window_dfrac`, and the only guard was
  `window_dfrac > 0`. A re-rip is a *second* cyanrip invocation, so album progress first
  went **backwards** (94.79% → 29.35%) and then **froze** at 35.45% while work continued;
  a frozen bar still wobbles by a rounding step, and 0.01 percentage points is greater
  than zero, so an hour of remaining work was divided by noise. Three fixes, each with its
  own test: a **floor** on the progress delta before its rate is believed (below it the
  last estimate is *held* rather than reinvented — the honest answer when the rate is
  unmeasurable); **restart detection**, so a backwards jump resets the rate window instead
  of averaging two different scales; and a **sanity ceiling**, above which no estimate is
  shown at all, because "about 62 hours left" is worse than silence — the user cannot tell
  a bug from a slow disc. Includes a test that replays the field trace's own percentages
  through the real estimator.
- **A truncated embedded log kept only the tail, dropping the rip's own opening** — the
  argv we spawned, the drive and disc detection, the settings in force. Now keeps **head
  and tail** with a **counted** elision marker, per the diagnostic-completeness rule: *a
  silent truncation reads as completeness*.

### Changed
- **Log retention raised from ~6 MiB to ~88 MiB** (`1 MiB × 5` → `8 MiB × 10`), answering
  the maintainer's question about whether the 1 MiB split was sound. It was not: one
  14-track rip writes enough that a few sessions evicted the oldest file, rotation is **by
  size alone** (not per session, not per version), so the eviction is silent and the file
  that scrolls away is the one holding the rip you are trying to diagnose. Three of the
  four log files uploaded were within **70 bytes** of the 1 MiB rotation threshold
  (1048542 / 1048506 / 1048548 of 1048576) — i.e. rotated at the limit, which is the
  tell. (Corrected from "exactly 1 MiB": `RotatingFileHandler` rolls over *before*
  exceeding the cap, so a full file lands just under it, never on it.)
- **The report's embedded-log limits are now runaway backstops, not routine caps**
  (10k lines → 200k; a new 8 MiB byte budget). An earlier revision of this change capped
  the block at 256 KiB to shrink a 1.5 MB report; the maintainer corrected it — *"I did
  tell you to capture more error data than you think you need"* — and the arithmetic
  agrees: 1.5 MB of diagnostics sits beside ~400 MB of FLAC for the same album, so the
  report is 0.4% of what the rip already wrote. A verbose 14-track rip is now embedded
  **whole**.
- **The cyanrip test pin stays `f5e11ba`**; this release changes only Platterpus.

## [0.6.4b6] — 2026-08-05

**A pre-release paired with cyanrip `f5e11ba` (`0.9.4-rc1+platterpus.5-beta.4`) — cutting edge
on both sides, by maintainer directive.** The previous beta paired with the fork's
*conservative* build; that was overruled on purpose, because the fork's A2 denominator change
**cannot be verified anywhere except a real disc with an AccurateRip entry**, so a conservative
session would leave the one unverifiable change unverified and still need a second session.
This release ships *our* half of that change, so both sides of the seam move together for the
first time this round. Round 7 is still OPEN, `--release-gate` still refuses a stable release,
and the production cyanrip pin does not move.

### Changed
- **The cyanrip test pin moves to `f5e11ba` (`0.9.4-rc1+platterpus.5-beta.4`)**, retiring
  `e61e75a` into `SUPERSEDED_TEST_PINS` one lap after it arrived. `c5fb909` and `e61e75a` both
  stay listed — a rig that has not rebuilt still gets `--consumer`.

### Fixed
- **The offset-variant tally no longer asserts a denominator that changed meaning under
  us.** The cyanrip fork's `f5e11ba` (round 7 lap 25 §A2) makes
  `Tracks ripped partially accurately:` divide by the disc's track count instead of by the
  tracks *not fully verified* — the same disc that printed `1/1` now prints `1/14`. Our
  renderer *paraphrased* the old meaning ("N of M track(s) not fully verified"), so on such a
  log it would have read **"1 of 14 track(s) not fully verified"** on a disc where thirteen
  tracks verified exactly: not a parse failure, a confidently false sentence in an archival
  artifact. Fixed by not paraphrasing their fraction at all — the offset-variant tracks are
  now counted from the per-track `Accurip 450:` results and the population is the disc's own
  track count, both facts we hold directly and neither dependent on which binary wrote the
  log. When their numerator disagrees with our count, the sentence **says so** rather than
  silently rendering ours. Verified against the committed 2026-08-04 rig artifact (14 tracks,
  track 5 offset-variant, reported `1/1`) and revert-proved: with the old paraphrase
  restored, the file hash changed, the module still imported, and both new tests failed.

### Added
- **`partially_accurate_reported` in the JSON report (schema v20)** — the ripper's own
  fraction, verbatim, beside our sentence about it. A rendered sentence cannot be turned back
  into the number the binary printed, and two logs of one disc from two fork builds are not
  comparable without it.
- **Both wordings of cyanrip's cover-art warning are now recorded as knowingly ignored**, with
  the reason: cyanrip runs under `-N` with our tags supplied via `-a`, so its own MusicBrainz
  lookup never runs and the release ID is unset at cover-art time *by construction* — the line
  is expected on every rip we produce and we fetch cover art ourselves. Matched on the tail the
  fork deliberately kept stable across the `f5e11ba` rewording. (Answering their lap 25 J2: we
  had never matched that string at all, so their A1 change is free for us.)
- **Two tests pinning the concurrent-lap collision.** Both projects independently numbered a
  lap 25, neither having received the other's file. The shared protocol says a round's state is
  *"its latest lap's verdict — by declared number"*, which at a tie names two files. Measured
  rather than reasoned: harmless, because each side's verdict is read from that side's own
  directory. The tests assert a same-lap collision still closes on bilateral GO **and** cannot
  hide the peer's HOLD — the direction where a tie resolved toward releasing would matter.

## [0.6.4b5] — 2026-08-05

**A pre-release, paired with cyanrip `e61e75a` (`0.9.4-rc1+platterpus.5-beta.3`).** Cut so
the next rig session tests a *declared pair* rather than a new ripper against the previous
app — the fork's lap 24 §E1 ask. Round 7 is still OPEN, `--release-gate` still refuses a
stable release, and the production cyanrip pin does not move.

### Added
- **The cyanrip test pin moves to `e61e75a` (`0.9.4-rc1+platterpus.5-beta.3`)**, retiring
  `c5fb909` into `SUPERSEDED_TEST_PINS`. `c5fb909` is what the 2026-08-04 rig actually ran,
  so it stays listed — a rig that has not rebuilt still gets `--consumer`. Its successor is
  **observably identical** to it: the fork measured log body (275 lines), cue sheet, decoded
  PCM and the `-j` record side by side, so the parity evidence transfers and the disc parity
  does not need repeating. The one code change is a `dev_path` leak on argument-validation
  refusals, which had made their sanitizers unusable and touches no line we parse.
- **`scripts/rig_session.sh` — the unattended half of a rig session.** The fork's lap 24 §E2:
  *"the rig session is the scarce resource; anything that runs unattended and writes an
  artifact is worth more than a checklist line."* So identity probes, the
  `-dirty`/`-grelease`/`-gunknown` banner check, `--doctor`, the fork's `-x` and `-j` (which
  our argv surface never sends), A25 pre-gap screening, a log snapshot taken **before**
  rotation silently eats it, `--audit-rips` and `eac_parity.py` all moved into one script.
  It **never stops on a failure** — a failing step is data — records every exit code
  including the successes, and writes an artifact per step so a step that did nothing is
  distinguishable from one that passed. Smoke-tested with every binary absent: exits 0, all
  ten artifacts present, six failures recorded rather than hidden.
- **`docs/rig-session-e61e75a.md`** — the session reduced to three human steps and one
  command, with a *proves / does not prove* table per step so a green run cannot be read as
  broader coverage than it is, and the three things nothing in the session can prove stated
  outright.

### Fixed
- **The go-first deadlock was ours, not the shared spec's.** Lap 23 reported that protocol v2
  cannot express a first `GO`, because writing one made our own conformance test fail:
  *"declares GO but peer verdict is 'HOLD', not GO (§5)"*. The fork tested **their** loader
  against the identical case (their lap 24 §B1) — accepted as well-formed, correctly refused
  as a close — and they were right. Our **gate** was never wrong: `round_status` requires both
  verdicts and `--release-gate` exits 1. Only `check_wire_header` was, because it conflated
  **well-formed** with **closable**. A GO whose *peer* verdict is not yet GO is now a *ready*
  declaration rather than a malformed file; **every other close-blocker stays a problem**,
  because every other one is the author's own gap (a missing identity field, no
  `HANDSHAKE-TESTED`) while the peer's verdict is the one thing the author cannot fix by
  editing their own file. §5's intent survives: `close_blockers` still names it, `--status`
  still shows it, and the round still does not close. Agreed for the round-8 bump in
  preference to a new `READY` token, which would meet gates that have not shipped the new
  spec and be treated — correctly — as *not agreement*.

- **The 2026-08-04 rig session's results are committed as a derived record**
  (`docs/handshake/artifacts-round-07/rig-session-results-c5fb909.md`) with the rip log, the
  auto-fix addendum, the cue, the rendered EAC-compatible log and the JSON report beside it.
  **14/14 bit-perfect against EAC's committed baseline**, `ripper_log_verification: verified`,
  and the first hardware sightings of `Read stalls:` and `C2 errors: unsupported by drive`.
  Every value in the record is read out of an artifact and names which one; steps that did
  not run say **NOT RUN** rather than leaving a blank, because a blank reads as a pass.
- **A25 closes as PASSED, and its premise had expired.** It said our 89× pre-gap bug *"has no
  hardware proof and this disc cannot give it one"*, because cyanrip reported `none` for all
  fourteen tracks. The fork now reads pre-gaps from the sub-channel, so ten tracks report a
  non-zero `Pregap LSN` — track 2's is `14327` against a true length of `160`, exactly the
  case the bug was about, and we render 160. **The screening command in the session sheet was
  corrected with it**: `Pregap LSN` ≠ `none` is now satisfied by almost any disc, so the
  discriminating string is `Pregap source: TOC`. Across the retained log history there are
  40+ source lines and **zero** say `TOC`, so the fork's C1 fix is recorded as
  hardware-unprovable on this collection rather than untested.
- **`docs/rig-session-c5fb909.md`** — an ordered, fill-in session sheet for one *named*
  pair (`v0.6.4b4` + cyanrip `c5fb909`), written at the maintainer's request as a front
  page for the 40-case `hardware-test-checklist.md` rather than a replacement for it. Six
  steps, cheapest evidence first, and it states plainly what the session **cannot** prove:
  the beta's single log-text change needs a disc whose **TOC** declares a pre-gap, and the
  baseline disc's is a lead-in. Anchors the rip against **EAC's committed baseline** rather
  than against the previous cyanrip run, because two runs of related builds agreeing is the
  shared-ancestor trap. Every step has a null-case blank, since a blank reads as a pass.

### Fixed
- **`--consumer` was never sent to the ripper, on any build, in the project's entire
  history.** `_build_rip_argv` gates it on `consumer_tag_for_build(ripper_build_tag)` and
  defaults that parameter to `""` so an unknown build gets no capability-gated flags — and
  **nothing ever passed it.** The parameter's own comment said defaulting to empty *"is
  what makes the safe behaviour the default rather than something a caller must
  remember"*; no caller remembered, so the safe default became the only behaviour and a
  fully-built, fully-tested capability (`accepts_consumer_flag`, the build allowlist,
  `assert_consumer_tag_is_sane`) hung off a value nobody supplied — the `RipHandle.cancel`
  shape from rule 9, a working mechanism reachable from nowhere. **Every existing test
  called `_build_rip_argv` directly and passed a tag**, so they measured the gate and never
  the wiring. Found in the 2026-08-04 rig artifact, where the fork prints the field:
  `Consumer: not identified (no --consumer given)`. `rip()` now supplies
  `_observed_build_tag()`, which already existed for `verify_log` and is best-effort (an
  unreadable banner still withholds the flag — the same fail-safe direction, now reached by
  measurement rather than by omission). The new test drives the real `rip()` entry point and
  asserts **both** directions: sent to `c5fb909`, withheld from an unrecognised build.
- **Three CLI tools read a rip log without its auto-fix addendum, and one of them
  therefore gave a wrong answer to the project's headline question.** Found by running
  `scripts/eac_parity.py` over the 2026-08-04 rig rip of the EAC baseline disc: it reported
  **13/14 — NOT parity**, naming track 5's CRC as `6902BCF0`. That is the read Platterpus
  **discarded** after re-ripping the track; the file on disk is `E0036697`, which is EAC's
  own value, and the rip was **14/14 bit-perfect**. A false negative on "is Platterpus
  bit-perfect?", from Platterpus's own checker. `render_eac_log.py` and `rip_report.py` had
  the same read — so the *archival* EAC-compatible log and the regenerated report were
  exposed to it too. The app itself was always correct; only the standalone scripts were
  wrong. All three now go through one shared `rip_addendum.read_any_log()` (encoding
  sniffed **and** addendum applied), because three copies of a read is three chances to
  forget the sidecar.
- **The sweep that was supposed to prevent exactly that had two holes, and the second is
  the one that bit.** `tests/test_rip_addendum.py` (a) globbed `src/platterpus/` only, so
  every tool in `scripts/` was outside every guard the rule has — CLAUDE.md §5.o again,
  *enforce a rule across the codebase, not at the place it was learned*; and (b) triggered
  only on `parse_cyanrip_log`/`parse_rip_log`, so a module that opened a log and pulled
  per-track CRCs out of it by any **other** route was not *exempt*, it was **unseen**.
  Widening both immediately found the two further offenders above — a check that had been
  green while three tools broke the rule it enforces.
- **Routing those scripts through a never-raises reader silently removed their error
  path.** `read_any_log` returns `""` for an unreadable log by contract, so the
  `except OSError` that printed `cannot read <path>` and exited 2 became unreachable —
  a clear diagnostic replaced by an empty read. Caught immediately by the existing
  `test_cli_missing_file_returns_2` in two files; the readability check is now explicit
  and before the read, and an empty result is reported rather than processed.
- **The rig session sheet now says how to *get* to `b4`, not just that you need it.** The
  in-app updater does it, but **only after switching to the beta channel** — `stable` never
  offers a pre-release, so "Check for updates" on the default setting correctly reports you
  are up to date. Written out with the three behaviours worth knowing first: it is a full
  ~242 MB download (the `.zsync` is for external `AppImageUpdate`, not for us), it always
  installs to `~/Applications/` regardless of where the AppImage you launch lives, and the
  fail-closed signature gate is dormant so SHA-256 is the integrity check. Every command in
  the sheet now names the same `~/Applications/` path the version check verifies — an update
  that lands there while you keep launching a copy in `~/Downloads` looks exactly like a
  successful update until a rip reports the wrong thing.
- **`update_signing.py` now records that arming the gate is a two-sided change.** Baking in
  `PUBLIC_KEY_B64` makes the installer refuse any release with no `.minisig` — which is
  every release published so far. The commit that sets the key must also make the release
  workflow publish `.minisig`, or the first signed release silently breaks in-app updating
  for everyone on the previous build. Fail-closed is right; shipping half of it is not.
- **Corrected a flag confusion that had been live in the project's notes and in a chat
  answer: `-O` and `-x` are different flags and only one is ours.** `-O` is force overread
  — our Settings toggle, and the subject of H10/F2. `-x` / `--cache-probe` is the fork's
  cache probe, which our 16-flag argv surface does not contain and Platterpus cannot
  invoke; `cyanrip_backend.py` already recorded that the `-x` older project notes named
  *"does not exist in cyanrip's getopt at all, so passing it would abort every rip."* The
  new session sheet leads with the distinction so a rig session does not try to reach the
  fork's probe through the app.

## [0.6.4b4] — 2026-08-04

**A pre-release, cut on the `--prerelease` path while handshake round 7 is OPEN.** It
claims no joint verification: `--release-gate` still exits 1 for a stable release, and the
production cyanrip pin does not move. Its purpose is to carry the **moved test pin** to the
rig — the wizard and `--install-ripper` read a constant that ships *inside* a release, so
before this build there was no in-app route to `c5fb909` at all, and a hand-built
`c5fb909` would have had `--consumer` withheld and its log verification reported
`not_determined`.

### Added
- **The cyanrip test pin moves to `c5fb909` (`0.9.4-rc1+platterpus.5-beta.2`), and
  `9003e6f` joins the superseded list.** The fork's lap 21: *"INSTALL `c5fb909`, NOT
  `9003e6f`."* One constant (`FORK_TEST_PIN`) drives the wizard target,
  `--install-ripper`, and the `--consumer` / `--verify-log` support sets. `9003e6f` is
  retired rather than deleted because it is the pin a rig is most likely to still have
  built — it held for thirteen laps and it is what the 2026-08-04 hardware session ran,
  so every artifact we hold from a real drive came from it. The **production** pin does
  not move: round 7 is open and both sides declare HOLD.
- **The handshake ordering rules are documented where a reader will look**
  (`docs/handshake/README.md` → *Ordering*), as four rules with the spec section each
  comes from, plus the two states the gate refuses rather than orders. A naming
  convention without its ordering rules is a format both sides can honour while reading
  it differently — which is the state both projects were in for one lap without knowing.
- **The ripper now verifies its own log, and the report carries its verdict
  (`ripper_log_verification`, schema v17 → v18).** Every other claim in a Platterpus
  report is our measurement of our own work. This one is not: `cyanrip --verify-log`
  checks *its* file against *its* checksum with *its* code, which is the only
  configuration in which a pass means anything. Tri-state (`verified` / `failed` /
  `not_determined`), with the exit code (`null` for a child never reaped, never `0`),
  the exact argv as spawned and the complete output, so a `failed` verdict is
  checkable rather than an accusation the user must take on trust. A `failed` verdict
  raises an `issues[]` entry and a WARN in the audit; a rejected *flag* is classified
  `not_determined`, never `failed` — a build that does not know the flag cannot be
  reporting a bad log, which is upstream's `-V` lesson pointing the other way. Runs
  on the rip worker's thread, never in a GUI slot; the audit check reads the recorded
  verdict rather than spawning a container exec inside `write_report`.
- **`--audit-rips` gained `ripper_log_integrity`, and the old `log_integrity` is
  renamed `our_log_integrity`.** Two checks, deliberately not merged, so a pass on the
  one we control can never imply a pass on the one that caught a real defect. The old
  name read as *"is the log intact"*, which is precisely the claim it was not making.
- **The consumer contract now enumerates the probe invocations too, not only the rip
  argv.** `--verify-log` and the version-flag tuple are derived from the same
  constants the code uses. A renamed flag is indistinguishable from an absent tool —
  that is how upstream's `-V` removal turned a working fork build into *"cyanrip is
  not installed"* — so leaving our two most failure-prone invocations out of the
  document we publish as *"this is what we send you"* was the same gap one layer up.
  `tests/test_argv_surface_agreement.py` now checks `--verify-log` against the fork's
  published flag table individually, with the version *fallback* tuple exempt for a
  stated reason and a test keeping that exemption from widening.

- **One place that answers "did anything go wrong?" — `diagnostics.py`, and a
  `diagnostics` block in the rip report (schema v15 → v16).** Diagnostics used to be
  spread across `outcome.failure_hint`, `log_parse.note`, `ctdb.error`, the per-track
  `issues` and five verification sub-blocks, none of them enumerated — so answering
  that one question required knowing where to look, and a fact captured in the log but
  absent from the JSON (or the reverse) read as *nothing happened*. Now every subsystem
  records a `Diagnostic` (severity, namespaced `subsystem.what` code, message, detail,
  tool, exact argv, tri-state exit code, where) through **one call that writes to two
  sinks** — the text log *and* the report — so the two artifacts cannot describe the
  same event differently. Placed third in the JSON, ahead of `outcome` and the verdict,
  because it is the first thing anyone debugging a rip should read.
  - Four rules are encoded rather than remembered: *recording also logs*; *never
    raises* (a collector that can throw turns a diagnosable failure into a crash);
    *truncation is stated* (bounded head **and** tail with a counted elision — a silent
    truncation reads as completeness); *tri-state* (`null` for an exit code we never
    collected is a real answer and is never written as `0`). Thread-safe, because
    workers record from their own threads.
- **Eight new `issues[]` checks — each one a fact that could be true while the list a
  triager opens first said "nothing to flag".** `issues[]` is the report's declared home
  for "what went wrong", and every one of these was somewhere else in the same file:
  `recompress_failed` (the step that **rewrites archival masters** was not even a
  parameter of the deriver), `verification_step_did_not_run`, `derived_incomplete`,
  `ripper_log_unparsed`, `track_count_mismatch`, `ripper_handshake_{approval}` (the
  entire v15 handshake block was read by *nothing*), `ripper_exit_unknown` /
  `ripper_nonzero_exit_on_success`, `artifact_unavailable` and
  `dependency_below_minimum` (`min_version_met: false` was the only per-tool failure
  signal in the whole report and nothing surfaced it). Nine regression tests, one per
  code, so none of them can go quiet again.

- **Every post-rip tool failure now carries the tool's own words — `adapters/tool_run.py`.**
  `flac_verify`, `transcode` and `flac_recompress` each declared their injected command
  seam as `Callable[[list[str]], int]`. An `int` — which made it **structurally
  impossible** for the dependency's output to reach the result, the JSON report or the
  user: each adapter's default runner captured stderr, logged a line or two, and dropped
  the rest before returning. So "⚠ FLAC verify FAILED for 3 file(s): a, b, c" named the
  *files* and could not name **what `flac` said about them**. Not an oversight at a call
  site; a missing channel, and no amount of care at the call sites could have closed it.
  - `ToolRun` carries the **exit code (tri-state)**, the **exact argv as spawned** and
    the **complete output with stderr merged** — the four facts CLAUDE.md's
    diagnostic-completeness rule names — and it is shared by all three adapters rather
    than copied into each, because four facts drift to three the moment there are three
    copies of them.
  - **A third state beside "exit 0" and "non-zero":** `started`. A missing binary is a
    problem with the *pass* (blame nothing, abort), a timeout is a problem with *this
    input* (blame the file, continue). Collapsing them is how a missing `flac` came to be
    reported as a corrupt FLAC, and the old code had no way to tell them apart.
  - The report's `verification.*` blocks gain `failure_details` — per failed file, the
    exit code, argv and complete output. The rip pane quotes the reason instead of
    listing filenames. `flac --test` no longer runs with `--silent`, which suppressed
    precisely the message this pass exists to be able to quote.
  - Three failures that used to read identically now read differently: the tool refused;
    the tool **claimed success and wrote no output file**; the encode succeeded and the
    **atomic swap-in** failed. The second is the alarming one and was invisible.
  - A timeout now **names the duration it exceeded**, so a wedged drive is
    distinguishable from a bound that is simply too tight for the disc.
- **The head-and-tail output cap lives in one place** (`diagnostics.bounded_output`).
  It had been written three times with three different limits, one of them head-only —
  and a head-only cap drops exactly the last line, which is where a tool puts its fatal
  message.
- **The diagnostics grep hint names the real log path.** It hardcoded
  `~/.local/share/platterpus/log.txt` while `paths.py` honours `XDG_DATA_HOME`; a hint
  pointing at a file the user does not have is worse than no hint, because they conclude
  the log does not exist.

- **One place that tells the user *where to look* — `ui/failure_text.py`, plus a sweep
  that keeps the tree honest.** ~20 modal failure reports said *"see the log"* and named
  **no path**; two named a typed-out `~/.local/share/…/log.txt` literal, which is wrong
  under any relocated `XDG_DATA_HOME` — and a path the user does not have is *worse* than
  no path, because they conclude the log is missing. **The two that tried hardest were
  the two that got it wrong**, which is the tell: the failure was not twenty forgetful
  authors, it was that there was nothing to call. The pointers are now built from
  `paths.LOG_PATH`, and `tests/test_failure_surfaces.py` sweeps every module for a
  message that points at "the log" without naming it — with a floor on the examined
  count, because a sweep that finds nothing because it looked nowhere is decoration. The
  sweep found six live sites beyond the ones the audit listed, including the desktop
  notification, and its own first version fired on a *comment* documenting a fix, which
  is the converse trap in miniature.

- **Help → Copy diagnostics… — the copyable surface the UI simply did not have.** The
  audit found **no** export, bundle or copy-diagnostics action anywhere in the app; the
  only clipboard call in the whole UI tree copied a *package search string*. The per-rip
  `.platterpus.json` **is** the richer bundle, but it exists only for a rip and is
  reachable only from the rip pane — so a setup failure, a dependency-check crash, a
  failed update or a drive probe had nothing to copy. The new dialog shows the version
  *pair*, the live environment and every diagnostic recorded this session, read from the
  same collector the report reads so the pasted text and the JSON cannot disagree. It
  renders the tri-state exit code as *"none (no child was reaped)"* rather than `0`,
  states its own truncation, distinguishes *"nothing recorded"* from *"everything
  verified"*, and says so when the dependency check has not run rather than showing an
  empty section. `build_diagnostics_text()` is pure and never raises — a diagnostics view
  that cannot open fails exactly when the user is already reporting a failure.
- **The one place cyanrip's own fatal sentence is displayed is now selectable.** The rip
  pane's status label had no `setTextInteractionFlags`, so the single most useful line in
  the app could not be selected by mouse or read by keyboard. `main_window_drive.py`
  already did this for its diagnosis box; this label was written without it.
- **`run_capture` records its own failures.** The argv went to DEBUG — which `log.txt`
  does not keep by default — so on a stock install a probe that could not find its binary
  left the exception message and nothing else. A non-zero probe exit is now recorded too,
  at *warning* (some callers legitimately read a non-zero exit as an answer): a probe
  whose exit code nobody looked at is how *"the tool is missing"* came to be reported for
  a tool that was present and had merely rejected a flag.
- **The collector is wired into every subsystem that can fail — and a sweep proves the
  call sites are reachable, not merely present.** A collector nothing calls is an empty
  section that reads as *"nothing went wrong"*, which is the same false-negative the
  `cancel()` audit taught: *grep for a call site before believing it works, and check it
  is reachable.* Now recording: the ripper (a start failure, a stream failure, **every**
  matched fatal rather than only the first, a non-zero exit with its argv and complete
  output, and an unreapable child as a real `null` exit code); the dependency probe;
  `metaflac`; the cache probe; CTDB; MusicBrainz (one helper for all four raise sites, so
  they cannot describe the same failure differently); Cover Art Archive — at `info` when
  the release genuinely has no art and `warning` when we could not find out, a distinction
  the reason code already carried and no severity reflected; and the library move.
  `tests/test_diagnostics.py` asserts each module both imports the collector *and* names
  its code — the pair is the check, since a label match alone answers "did they name it"
  and not "did they write it". Its own first version reported `ctdb_client.py` as unwired
  because the import shares a line; it reads the AST now, because a matcher narrower than
  the language produces confident wrong answers, and a false failure trains people to
  ignore a check as surely as a false pass lets a bug through.
- **`report_types.py` describes the whole report again, and a sweep keeps it that
  way.** It calls itself *"the single source of truth for the structure `rip_report`
  writes"*, and it was missing `RipReport.completeness` and `RipReport.artifacts` (four
  schema versions late), all four of `TrackBlock`'s pre-gap provenance keys, three
  `DiscBlock` `medium_*` keys — including `medium_undetermined`, the **only** field that
  says a rip's titles may belong to another disc — and `TimingBlock`'s
  `realtime_multiplier_basis`, which changes what the ratio is measured *against*. None
  of it was a type error, because the emit site is not annotated as the `TypedDict`, so
  mypy had nothing to compare. The existing test anchored **three** blocks by hand, which
  is the same invisible-by-omission promise the drift itself was; it now builds a real
  report at runtime and requires a declared field for every key of every nested block,
  with floors on both the block count and the key count. Runtime rather than AST on
  purpose: `realtime_multiplier_basis` is added *after* the dict literal is built, which
  is exactly how it hid from a source-level check.

- **The auto-fix addendum no longer breaks `cyanrip --verify-log`.** After the
  per-track auto-fix swapped a converged re-read in, we appended a supersede block to
  cyanrip's own `.log`. That file ends with a `Log FUN512:` self-checksum and
  `--verify-log` **rejects trailing content by design**, so every auto-fixed disc
  shipped a log the ripper itself would call modified. The record now goes to a
  sidecar — `<log stem>.platterpus-addendum.txt` — and the ripper's log is left
  byte-exact. `platterpus.rip_addendum.read_log_with_addendum` is the single
  sanctioned way to read a rip log back, because a re-parse that skips the sidecar
  gets the checksums of bytes the auto-fix deleted (the original bug the addendum
  existed to prevent, and the trap moving it created); a source sweep enforces that,
  since the rule decays and the test does not.
  - Found by the cyanrip fork reading a real rig artifact. **The question had already
    been asked and answered** — round 5 asked whether an addendum could follow the
    checksum line, the answer was no, and they pinned it with a test — and our own
    integrity check could not see it, because it verified a file we wrote against a
    checksum we computed. A closed loop agrees with itself.
- **The addendum now supersedes the whole per-track record, not just the CRC.** The
  archived AccurateRip v1/v2, the offset-variant result and the secure-re-read verdict
  all described the read that was discarded; on the rig that meant `7CE3F6E7` and
  `268CCD94` standing beside a shipped file whose real values were `F5426D5F` and
  `9EEB8843`. Extending the old block field by field would have been the wrong fix.
- **`ripper_handshake_approval` returned `not_determined` on every real fork rip — a
  wrong verdict, not merely a terse one.** The parser splits the banner (`log_creator`
  without the parenthetical, the tag in `ripper_build`), and the approval matcher read
  only the half with no `(`, concluded *"no build tag"*, and shrugged about a build it
  had already extracted and could name. The same log, given its full first line,
  returns `unapproved` and explains that `9003e6f` is the round-7 test pin. The test
  written the same day passed because its fixture set `log_creator` to a *whole*
  banner — a shape the parser never produces. The regression now reads the committed
  rig log, so the stand-in cannot be more capable than the product again.

### Fixed
- **The version pair line named the ripper twice.** `version_pair_line()` — the
  maintainer's *"include what versions you both are"*, rendered into the Copy-diagnostics
  bundle — produced *"Platterpus 0.6.4b3 + cyanrip cyanrip 0.9.4-rc1
  (platterpus-fork-g2f950c8)"*. Two renderers both prefixed `cyanrip ` to a banner that
  already begins with it; both now go through one helper, so the assumption lives in one
  place instead of two. **Both of its tests were green and could not have failed** — each
  asserts *containment* of the banner, and `"cyanrip cyanrip 0.9.4…"` contains `"cyanrip
  0.9.4…"`. The new test counts, across both renderers and all three banner shapes. In the
  one string whose whole job is to be quotable into a bug report.
- **Our handshake ordering diverged from the shared spec in two places, and both had
  been normative since the spec file was created.** The fork's lap 20 asked us to *diff*
  their three ordering rules against ours rather than agree in principle; doing it found
  that (1) `sort_key`'s **round** half read the *filename* while its lap half already read
  the header — `handshake-protocol.md` §3 says *"by declared number, never by filename or
  mtime"* — and (2) a file declaring no `HANDSHAKE-LAP` fell back to its *name* rather
  than to lap 1, which §3 sets in the same sentence. Neither changed the order of any file
  either project has ever had, which is exactly why only a comparison could find them: a
  difference that changes no observable behaviour is invisible to every test either side
  can write. **A spec statement with no conformance row went unimplemented for the whole
  life of the spec.**
- **Removing that filename fallback opened a fail-open direction, so the gate now refuses
  two states rather than ordering them** (`handshake.ordering_blockers`, consulted by
  `--status` and so by `--release-gate`, naming the file and the rule for each). A v2 file
  that omits its required `HANDSHAKE-LAP` sorts *oldest* under §3, so a later `GO` would
  be read as a round's newest word while that file's `HOLD` sorted underneath it — §2 rule
  4, an absent required field fails closed. And a file whose declared round is not the
  round it is filed under (§3, §8 row 10) is now refused instead of voting in a round it
  says it is not in — a state reachable *only because* the round half became header-first,
  so the fix's own new state got its own test. Grandfathering is derived from the absence
  of a `HANDSHAKE-PROTOCOL` line, not from a list of round numbers that stops covering
  files added after it was written.
- **`tests/test_argv_surface_agreement.py` had been diffing our argv against round 6's
  flag table since the 2026-08-04 rename.** It grouped inbound files with the
  *grandfathered* `round-6` / `round-6b` regex, which does not match `round-07-lap-NN.md`,
  so **all of round 7 was invisible to it** — measured, not inferred: the label read
  `round-6.md + round-6b.md + round-6c.md` while the fork was on lap 21. That was the
  fourth place in the repo to grow its own round parser and the fourth to break on the
  same rename; it now uses the shared `round_number()` and `sort_key()`. **The guard
  written to catch exactly this had inherited the same blind spot** — it computed "the
  newest round on disk" with the same regex, and its final assertion (`used_round <=
  newest_on_disk`) *could not fail*, because the used round is drawn from the on-disk set.
  Replaced with a recorded lag ratchet that may shrink but never silently grow, plus a
  regression test that asserts the **production** grouping, not a copy of it, can see the
  newest round.
- **`--emit` produced a file `--check` refuses.** The emitted skeleton omitted
  `HANDSHAKE-PROTOCOL`, the *first* entry in `REQUIRED_WIRE_FIELDS`, so our own generator
  failed our own §3 header check — and `check_outbound` sweeps sections rather than the
  header, so the existing "our skeleton satisfies our own spec" test stayed green. The new
  test derives the expected fields from the required-field tuple and asserts through
  `check_wire_header`, so the next added field cannot skip the emitter quietly.
- **An ordering test that passed for a reason unrelated to its claim.** It handed `_lap_of`
  two `Path`s that did not exist, so the lap it read for `round-07-lap-16.md` came from
  the very filename fallback this change removes. Rewritten against real files on disk —
  identify the subject the way production identifies it.
- **Two divergences between our handshake loader and the fork's, found by comparing
  implementations rather than by a failing test.** Their lap 18 adopted our naming
  convention and reported how *their* loader orders files; ours did it differently in
  two places. (1) A file declaring no lap was **lap 0** for us and **lap 1** for them —
  same ordering on today's tree, so nothing failed; theirs is more correct, since a
  round's pre-lap-header file *is* that round's first lap. (2) An **ambiguous**
  `HANDSHAKE-LAP` fell back to the *filename* for us, so it sorted at its named lap, a
  later valid file was read as newest, and **the ambiguity was never examined by the
  gate** — the protocol's own "present-but-ambiguous is worse than absent" broken in the
  direction that hides it. Both of their rules adopted; the ambiguous case now sorts
  last so the header check refuses it. Two implementations of one convention is the
  drift this protocol exists to prevent, and it is the only reason either was found.
- **A floor that expired because it required a tree state, not a property.** The
  mixed-scheme ordering test demanded a legacy-named file in round 7 — true when
  written, and the fork's lap 18 renamed theirs to `round-07-lap-01.md`, which we
  matched, so the floor started failing on a tree that was *more* correct. The
  mixed-scheme proof moved to the synthetic case, which cannot expire. Same for a test
  that located a committed artifact by filename rather than by identity.
- **Handshake files are named `round-NN-lap-LL.md`, and the old scheme had already
  destroyed one.** The letter suffix (`round-7f.md`) encoded nothing: the same letter
  meant **lap 12** in `inbound/` and **lap 10** in `verified/`, two files were both lap
  7 by coincidence, and filing a received file meant picking "the next free letter" —
  which overwrote lap 4 in this session and needed restoring from git. The name now
  states the round and lap from the file's own wire header, so the two are checked
  against each other (`tests/test_handshake_file_naming.py`); direction stays the
  directory's job; an amendment is a new lap, not a letter. Files predating the lap
  header keep their names, and the exemption is *derived* — a file with no lap has
  nothing to name itself with — with the converse enforced too, since a canonical name
  on a file that declares no lap is a false label. Inbound artifacts follow, naming the
  build their **own banner** asserts rather than the commit a lap file names them by.
- **One ordering for handshake files, because three copies of it were wrong at once.**
  "Which file is newer" was a plain stem sort in three independent places, and the
  rename broke all three: lexically `"round-07-lap-16" < "round-7"`. One of the three
  decides `scripts/handshake.py --status`, which reported round 7's `they-verified` as
  **GO** while their lap 16 declares HOLD — **a release gate saying an open round had
  closed, because of a filename.** Ordering is now `handshake.sort_key`, keyed on the
  *declared* round and lap rather than the string, and used by the script and both
  tests. Regression-tested with a floor requiring the mixed-scheme case the bug needed.
- **`rip.read_stalls_count` — the stall count, structured, and a `ripper_read_stalls`
  entry in `issues[]` when it is positive.** A rip whose read took 187 seconds is worth
  telling the user about even when every checksum came out right — that is how a disc
  goes from readable to unreadable — and until now the verbatim line was stored and
  surfaced nowhere. Tri-state: `0` the ripper measured and found none, `N` that many
  stalled, `null` not measured *or a shape we do not recognise*. The verbatim text
  stays the authoritative record and is never replaced by the number, because the four
  shapes are the fork's own, **derived from the code that prints them and not yet
  observed from any build** — so an unrecognised shape must degrade to `null` beside
  intact text, never to `0`.
- **`rip.read_stalls` — the fork's stall-watchdog verdict, verbatim (schema v18 →
  v19).** They added that line at their own initiative *for us*, and we were not
  reading it — while answering their design question about whether we wanted the
  figure per-track or disc-level. Answering a contract question from the design rather
  than from the code is the failure this round keeps circling, and it was found by
  running the real parser over their golden reference rather than by re-reading our
  own source. `null` on stock cyanrip, which never prints the line: a third state,
  because *no stalls measured* and *stalls not measured* are different claims. Kept as
  text rather than a parsed count — we have only seen the `none` shape, and a regex
  for the populated one would encode our guess at their wording, which is what put
  `merged` in the gap matcher for two rounds.
- **A handshake file that cites hardware must now name the pair the hardware ran.**
  Lap 8 declared the tested pair as Platterpus `0.6.4b1`; the rig ran `0.6.4b3`. The
  fork caught it by hand, and their diagnosis is the finding: *"nothing in either
  artifact would have flagged the mismatch."* The evidence was in the repository —
  `generator.version` in the report, the EAC log's header — and the declaration was in
  a file three directories away, with no code relating them.
  `tests/test_handshake_cites_the_pair_it_ran.py` now requires any handshake file
  citing `output_reference/<dir>/` to declare the app version **and** the ripper build
  tag that directory's artifacts actually carry. Read off the artifact's content, never
  off `__version__`, so a correct historical record is not refused after a version
  bump; and with a proof-of-failure case that runs lap 8's real declaration against the
  real b3 artifact and asserts rejection.
- **Corrected a disproven claim in our own source: the FUN512 footer and
  `--verify-log` did *not* arrive together.** `VERIFY_LOG_FLAG`'s range comment said
  *"all fork builds and stock ≥ 0.9.3 — the checksum footer and this flag arrived
  together."* The fork disproved both halves from their repository: `-Y` is
  **upstream's** (commit `443f749`, 2026-07-12), at which point `meson.build` still
  read `0.9.3`, and the footer landed in `757108c` which **predates** it — so builds
  exist that write the footer and cannot verify it, and a build reporting `0.9.3` may
  or may not accept the flag. The wrong version was an inference I had already
  labelled an inference and left in anyway; the correction is kept visible in the
  source rather than silently rewritten.
- **`--verify-log`'s failure classifier no longer keys on cyanrip's error wording.**
  It distinguished *"the flag was rejected"* from *"the log was rejected"* by matching
  `Unable to parse command line argument: …`. The fork pointed out that string is
  **genopt's, not theirs, and one upstream sync from changing**, and asked us to key
  on the exit code plus the flag's presence in their published table instead. A
  `failed` verdict now requires positive evidence the build accepts the flag
  (`fork_source.accepts_verify_log`, tri-state — `None` for unknown, never `False`,
  since no document says any cyanrip *lacks* it). Everything else fails safe to
  `not_determined`: the cost of that is a report line, while the other error accuses
  an intact archival log of being corrupt. The wording match is kept only as a belt
  that can soften a verdict, never reach one. Their point is a lesson we have watched
  from the other side — a matcher built on a dependency's prose is a hand-maintained
  list of shapes, which is what hid 16 of their fatal strings in round 5.
- **The two provenance witnesses are now actually compared.** Round 7 lap 10 told the
  cyanrip fork that *"when the two disagree, the disagreement is the finding"* about
  `ripper_handshake_approval` (our verdict on the build tag) versus
  `ripper_handshake_note` (the statement the fork's build system compiles into the
  binary) — and nothing in the code compared them. The note was parsed at schema v17,
  stored, and read by nothing: the same capture-without-surfacing defect the approval
  block itself had until they found *it* was read by nothing. An approved build whose
  own text says it is not a release now raises an `error` in `issues[]`, because one
  of two independent witnesses must be wrong and both possibilities are serious (a
  wrong pin, or a build tag naming a tree that is not what was built). The real
  artifact's state — unapproved, note agreeing — stays silent, so a deliberate
  test-pin rip does not cry wolf.
- **The EAC-style log's status report claimed more tracks than the disc has.** On the
  rig's 14-track disc it printed `13 accurately ripped` + `1 could not be verified` +
  `1 matched only an offset-variant pressing` = **15**. `unverified = total -
  verified` already contained every offset-variant track — an offset-variant match is
  not an exact match — and the third line counted those same tracks again. Each line
  was defensible on its own wording and the aggregate was arithmetically false, in a
  SHA-256-attested archival document. The three lines now partition the tracks and
  sum to the total; the wording is deliberately unchanged, because it is what the
  cyanrip fork diffs against and they asked that neither side reword unilaterally
  (round 7 lap 10, H4). The clean-sweep headline still keys on *anything short of an
  exact match*, so a disc of only offset-variant matches cannot announce "All tracks
  accurately ripped" — a precondition the partition fix created, with its own test.
- **`partially_accurate_summary` now names its denominator.** cyanrip's `Tracks
  ripped partially accurately: 1/1` counts tracks *not fully verified*, not tracks on
  the disc — the fork confirmed it — so `1/1` on a 14-track disc is correct and reads
  like a typo. We rendered it as *"1/1 tracks ripped partially accurately"*,
  inheriting the ambiguity and dropping even the positional hint the ripper's line
  had. It now reads *"1 of 1 track(s) not fully verified matched only an
  offset-variant pressing"*. The ripper's own line is unchanged.
- **Tools → Check dependencies could do nothing visible at all.** A crashed probe emitted
  `None` and the GUI half returned immediately, so a user-initiated menu action was
  indistinguishable from a dead menu item — with the traceback going only to a file that
  is INFO-only by default. It now says the *check* failed (not that a tool is missing),
  names the log, and records the exception with its traceback in the diagnostics block.
- **The two "did not complete" dialogs said four words and logged nothing.** Both the
  setup and uninstall dialogs have a branch for "not ready, and no step reported a
  failure" — the case nobody had considered, and therefore the least diagnosable message
  in each dialog. `uninstall_dialog.py` had **no logging at all**. Both now say *why*
  there is nothing specific to point at, name the log, and record every step's status.
- **The rip-failure report now carries the ripper's output and the session debug log.**
  This report exists for the rips that produced no log at all — the most-broken ones —
  and it passed neither `artifacts=` nor `debug_log=`. So on exactly those rips: the
  worker's `captured_stdout` (built with a head, a counted elision and a tail
  *specifically to survive a kill*) was discarded; the always-DEBUG session buffer was
  not embedded; and `log.txt` is INFO by default while every ripper line is written with
  `log.debug`, so it was not on disk either. The ripper's entire output existed in
  memory, in a variable the code already knew how to serialise, and reached neither the
  screen, nor the log file, nor the one artifact written — only the one-line
  `failure_hint` survived. The full-report path had passed both all along. Each embed is
  guarded separately so a capture that cannot be built cannot cost us the report, and the
  written path is now announced at WARNING **and on screen**, because a user asked to
  "send the report" has to be able to find it. Revert-proven.
- **`"Rip failed."` no longer clobbers the error text captured seconds earlier.**
  `_finish_rip` read only `worker.failure_hint`. On every start/stream failure the ripper
  produced no stdout, so that hint is empty — while the *specific* sentence had been put
  on screen by `_on_rip_error` and stashed in `_last_rip_error`, where the JSON report
  reads it and the status line did not. The one surface a user actually looks at was the
  only one that threw the diagnosis away. When there genuinely is nothing captured, the
  fallback now says so and names the log path instead of four words that name nothing.
- **A `giving up on track N` line no longer overwrites the ripper's own fatal.** The
  branch immediately above it is commented *"first error wins"*; this branch assigned
  unconditionally, so a verbatim cyanrip fatal matched one line earlier was replaced by
  canned "clean the disc" advice. The comment described a rule the code did not implement
  here. The tool's sentence now leads and the advice follows.
- **`metaflac` failures were captured nowhere at all** — and it runs on *every* rip
  (it is how the user's edited tags reach the FLAC and how the cover art is embedded).
  `MetaflacError` carried a sentence built from the last stderr line; the argv, the exit
  code and the rest of the output were discarded at the point of failure, three of the
  six call sites reduced the exception to a one-line warning, and one dropped its text
  entirely. So "your tags did not get written" was, worst case, a single line saying so
  with no way to find out why. The adapter now records exit code (tri-state), exact
  argv, complete output and a readable sentence into the diagnostics collector **before**
  raising, so the evidence exists whether or not the caller logs it — and the exception
  carries all four so a caller can render any of them. Also: an `OSError` (EACCES on the
  binary) used to escape as a raw `OSError` from an adapter documented to raise
  `MetaflacError`, so every caller's `except MetaflacError` missed it; `stdin` is now
  `DEVNULL`, because a `metaflac` that decided to prompt would hang the GUI with no
  explanation; and a timeout names the duration it exceeded.
- **`cd-paranoia -A`'s exit code was never read**, and its verdict feeds the archival
  *"Defeat audio cache"* field. "The tool failed" and "the tool ran and was
  inconclusive" both produced `defeat=None` with nothing distinguishing them — two very
  different facts rendered identically. The exit code is now recorded on the result
  (tri-state) and a non-zero exit raises a warning saying explicitly that this was a
  tool failure rather than an inconclusive measurement. The honest "unknown" verdict is
  unchanged; what is new is that the reader is told which kind of unknown it is.
- **`eject`'s own message was destroyed at the source, and the status line lied.**
  `drive_control._run_bounded` set `stderr=DEVNULL`, so *no* caller could ever report
  why an eject failed; the exit code was logged at INFO with the message gone, and the
  caller discarded the returned bool. A tray that never opened therefore left the rip
  pane reading *"Rip complete — ejecting the disc…"* indefinitely, with nothing above
  INFO in the log to contradict it. Output is now captured and merged, a failure records
  the full diagnostic, and the worker reports back via a queued `eject_finished` signal
  so the on-screen claim is corrected (and names the log path). Success stays silent —
  an open tray is self-evident, and overwriting "Rip complete" would bury the result.
- **A bare `except OSError: pass` could send a rip into the folder the user was
  avoiding.** `free_album_folder_templates` silently fell back to the *original*
  templates, so "rip to a new folder" could resolve to a folder that already holds
  audio — a permissions problem presenting as a product decision. It now warns, says
  what the consequence is, and records a diagnostic.
- **The drive-offset CSV's malformed rows are logged, as its docstring already
  promised.** The docstring said malformed lines "are skipped with a log note"; the
  row-level skip logged nothing, so a user whose CSV contributed nothing had no way to
  find the bad line. Bounded to five examples with the count stated, plus a distinct
  message for "every row was malformed" — which reads differently from "the file was
  empty" and has a different fix. A doc claim a reader relies on has to be true in the
  code; a comment where a check belongs is not a fix.
- **A `NameError` on the setup engine's own failure path.** The diagnostics call added
  to `host_setup.py` referenced a module that was never imported, so a *failed* setup
  step raised `NameError` from inside the code meant to explain the failure. Found by
  the suite, not by review — and it is the sharpest possible illustration of why the
  collector exists: the reporting path is code too, and it fails like code.
- **The `rip` and `log_parse` blocks are now built once, into locals.** They were
  assembled inline in the report's dict literal, so the `issues` list that claims to
  summarise them had no way to read them — which is why the entire handshake-approval
  block and the ripper's exit code contributed nothing. Same rule the verification
  sub-blocks already followed: one construction site, so the summary and the thing
  summarised cannot disagree.

### Documentation
- **`docs/error-reporting.md` — the design of record for how a failure becomes something
  a person can act on.** The four obligations and the code that meets each; the one
  collector that feeds the text log, the report and the copy-diagnostics dialog from a
  single call; the severity contract; the recipe for adding a failure path; and a table of
  what is *enforced by a test* rather than trusted. Indexed in `docs/README.md`.
- **The generated consumer contract now states the range its claims cover** — which app
  version produced it and which approved ripper build its rows were checked against. A
  contract claim with no stated range is a snapshot that reads as a fact: the fork's
  *"there is no `-V`"* was true when written and one commit from being the misleading
  kind of true. Sent to the fork as an ask in the same round, so we landed our own half
  first. The accepted cost is a two-line diff on a version bump, which is not spurious —
  the document really does describe a new version — and the docstring says so, to stop a
  future reader "fixing" it back.
- **Round 7 lap 10 sent** (`docs/handshake/verified/round-07-lap-10.md`, **HOLD** — the round
  stays open and the pin does not move). It states what we now capture and surface so the
  fork can hold us to it, and asks three things back, including our own view on their
  seven stdout-only refusal paths: document them as stdout-only rather than opening the
  logfile earlier, because a logfile opened before the disc is validated trades an old
  ambiguity for a new one.

### Verified on hardware — **full 14/14 EAC parity, and three defects the artifact caught**

The maintainer uploaded a real rip of the EAC baseline disc from the rig (2026-08-04):
Platterpus **0.6.4b3** + `cyanrip 0.9.4-rc1+platterpus.5-beta.1
(platterpus-fork-g9003e6f)`, Pioneer BDR-209D, offset +667. The four artifacts are
committed to `output_reference/cyanrip_fork_flac/` and
`tests/test_fork_rip_eac_parity.py` **reads them** rather than restating their numbers.

- **14 of 14 tracks are bit-identical to EAC.** Every `Copy CRC` equal, track for
  track, against the committed genuine EAC 1.8 log of the same disc in the same drive.
  That closes the parity goal in `output_reference/README.md`.
- **All ten of EAC's `Pre-gap length` rows match ours to the hundredth of a second, in
  order.** cyanrip 0.9.3 reported "None signalled" and found none; the fork reads them
  from the sub-channel and finds precisely EAC's ten. The KDD-32 / `INDEX 00`
  capability gap that `eac_log_export._gap_handling` documented as *our one measurable
  archival shortfall against EAC* is **closed for the fork** — and that docstring, which
  still described the shortfall as open, is corrected.
- **Track 5 reached parity only via the auto-fix.** Its first pass produced `6902BCF0`,
  which does not match EAC; only the `+450` offset-variant matched AccurateRip. The
  secure re-rip produced `E0036697` — EAC's value — and swapped it in. So the artifact
  is also the proof that the re-rip feature does the thing it exists for.

### Fixed — found by reading that artifact, all three invisible to a green suite
- **The EAC log's `Gap handling` row was wrong on every disc with a real pregap.** The
  fork prints `merging into track N`; our matcher looked for `merged` — one word ending
  — so the row read *"(not reported by the ripper)"* where EAC says *"Appended to
  previous track"*. The fork published `merging into track %i` in **round 5**, so the
  evidence sat in a committed file in this repo for two rounds; exactly the shape of the
  `-V` blocker. **Two** separate tests pinned the invented word, and
  `_gap_handling`'s own docstring already named this trap about the *previous* bug in
  the same function — *"its test could not catch it because the fixture handed the
  function a string cyanrip does not emit."* The replacement test made the same mistake
  with a different invented string. The matcher now uses the fork's five published
  actions, `dropping`/`splitting off` are refused an EAC phrase because they change what
  audio exists, and the tests read the published block out of
  `docs/handshake/inbound/round-6.md`.
- **`artifacts.ripper_stdout` was empty on every completed rip.** The report is
  re-written by each post-rip step; `_on_rip_finished` clears `_rip_worker` in between;
  and the writer read the live worker behind a guard whose *only* effect was to emit
  `""` once it was gone. So the first write carried the ripper's output and every later
  one replaced it with nothing — and since FLAC verify is on by default and the
  self-check always runs, the file the user ships always lost it. The block's own
  `source` string still promised *"complete even when the ripper was killed"*: accurate
  about the mechanism, false about the file. This is the one artifact the cyanrip
  project cannot produce for itself, and the thing round 7 lap 10 tells them we capture.
  Now snapshotted at finish like every other `_last_*` fact.
- **`self_check` was an undeclared top-level report key, and the sweep written the same
  day could not see it.** It is added by `write_report` *after* `_build`, and the
  completeness sweep inspected the **builder** — my stand-in — rather than a written
  file. The real artifact had 32 top-level keys where the builder produces 31. The sweep
  now writes a report and reads it back.

### Added
- **The fork's two self-describing log lines are parsed (schema v16 → v17).**
  `rip.ripper_handshake_note` is the binary's own compiled-in statement of which
  handshake round it was built from — the rig log says `round 7 lap 7 OPEN, verdict HOLD
  -- NOT a released build`, which is a provenance claim **derivable from the artifact's
  content** (CLAUDE.md rule 12) and a second, *independent* witness beside
  `ripper_handshake_approval`, which is only *our* verdict on the banner. When the two
  disagree, the disagreement is the finding. `rip.ripper_consumer` records who the
  ripper was told the caller was — `not identified (no --consumer given)` until we ship
  the flag, which is itself worth carrying, because a log with no consumer cannot be
  attributed to us at all. Both verbatim, both `null` on stock cyanrip. Implemented from
  the real artifact rather than a fixture, which is what made it possible: a fixture
  would have been my guess at their wording.
- **The real-log sweeps are build-aware.** They were written when every committed real
  log was stock 0.9.3, so *"the real logs"* and *"stock output"* were the same set — the
  state that let the fork's wording go unmatched for two rounds. `_stock_logs()` /
  `_fork_logs()` split them, a floor test requires **both** builds to be present, and the
  top-level-line sweep now stops at Platterpus's own auto-fix addendum rather than
  demanding ignore-list entries for our own prose.

### Verified on hardware
- **The `$HOME` fix works on the real rig.** After installing v0.6.4b3 the setup
  wizard reports every step ✓ — *"Platterpus fork of cyanrip (build + export) —
  installed"* — and the binary confirms it itself:
  `~/.local/bin/cyanrip --version` → `cyanrip 0.9.4-rc1+platterpus.5-beta.1
  (platterpus-fork-g9003e6f)`. Read off the binary rather than inferred from the
  wizard's verdict. The orphaned `~/'$HOME'` tree the bug created is confirmed present
  on disk and is now dead weight, which is the defect's own fingerprint.

## [0.6.4b3] — 2026-08-04

**The `$HOME` defect, found by the diagnostics b2 added.** b2's whole purpose was to
make the fork-build failure visible; it worked, and the answer was in the first log it
produced. Both of my earlier guesses were wrong — this is what it actually was.

### Fixed
- **The fork was built in a directory literally named `$HOME`, so its build tag named
  no commit.** `FORK_SOURCE_DIR` was the literal string `"$HOME/.cache/platterpus/
  cyanrip-fork"`, with a comment claiming the container's shell would expand it. It
  does not: the value arrived as a positional argument and the script did `src="$1"`,
  and **parameter expansion does not recurse** — so `$HOME` stayed five literal
  characters and every path became relative to a directory *named* `$HOME`. The user's
  log said so in plain text: `Source dir: /home/rmccann/$HOME/.cache/platterpus/
  cyanrip-fork`.
  - **The build otherwise succeeded** — correct commit (`9003e6f`), correct version,
    31/31 targets, installed and exported. Clone, configure, compile and install all
    used the same wrong string, so they agreed with each other. **Consistently wrong
    is the hardest kind of wrong to see**, and it is why this survived several rounds
    of inspection.
  - The single casualty was meson's `vcs_tag`, which could not resolve a git revision
    from that path and fell back to upstream cyanrip's literal `release`. So the binary
    reported `platterpus-fork-grelease`: **a build tag naming no commit**, which the
    verify step correctly refused. Exactly the failure CLAUDE.md rule 12 describes —
    *a build tag names a commit; it does not name what was built* — arriving on our
    side of the seam this time.
  - The scripts now expand `$HOME` **at the point of use** (`src="$HOME/$1"`), which is
    what the old comment believed was happening. `install_command` had to move to
    `sh -c` for the same reason: it "worked" only because it shared the same wrong
    literal, so fixing the build alone would have left it copying from a path that no
    longer exists. One expansion rule, applied in both places.
  - `assert_shell_safe_subpath()` guards the argv chokepoint: a path containing `$`,
    an absolute path, a traversal or a shell metacharacter now raises rather than
    reaching a shell. Per CLAUDE.md — enforced by code, not merely stated in a doc.
- **The verify step reported what it *expected* and never what it *saw*.** The
  observed banner was printed one line earlier on stdout, and `_run_commands` keeps
  only the last line for the UI — so the one fact that mattered was discarded at the
  moment it mattered. The error now quotes the observed banner, and a `-grelease` /
  `-gunknown` tag gets its own sentence naming the cause, because a user should not
  need to know meson internals to act on it. **This one string would have ended the
  hunt two sessions earlier.**
- **A silent success left no trace in the log.** `sudo install` produced no output, so
  nothing was recorded between the argv line before it and the argv line after it, and
  "did it run?" was unanswerable. Every command now logs its exit.

### Added
- **Build-step diagnostics, deliberately more than seems necessary.** The build script
  now reports `$HOME`, the working directory, the resolved source tree, the requested
  pin and branch; refuses a non-absolute or `$`-bearing source tree with a named
  fatal; prints `HEAD`, the short sha, `git describe`, and a **dirty-tree warning**;
  probes whether git is usable in the source root (the precondition `vcs_tag` needs,
  whose silent failure was this whole bug); and finally **reads the banner off the
  binary it just built** — so a wrong tag is attributed to the build that produced it
  rather than surfacing three commands later. The install step reports what it copied
  and the resulting file.

## [0.6.4b2] — 2026-08-04

**Beta 2, cut from the joint hardware session's first real run.** Everything here
came out of installing `v0.6.4b1` on the rig: two wrong messages and one missing
diagnostic, all found within minutes of the wizard being used for real.

### Fixed
- **Every setup command's output was captured and thrown away.**
  `SubprocessRunner.run()` logged the argv and discarded stdout/stderr;
  `HostSetup._run_commands` then reduced that output to its **last line** for the UI.
  So a failed `git`/`meson`/`ninja` inside the container left exactly one line of
  evidence anywhere in the system, and the log file a user is asked to attach to a
  bug report contained none of it. Found while trying to diagnose a real fork-build
  failure with nothing to work from. Captured-and-discarded is worse than never
  captured — the report still looks complete. Now: exit code + exact argv + complete
  output at ERROR on failure, and at DEBUG on success, bounded **head and tail** with
  a counted elision marker (a fatal message is the *last* thing a tool prints, so a
  head-only cap drops precisely the line that explains the failure).
- **The setup wizard said "✓ Setup complete — you can rip now." while a step had
  FAILED.** Real-user report on v0.6.4b1: the summary claimed success and, two lines
  below it, listed *"✗ Platterpus fork of cyanrip (build + export) — installed cyanrip
  does not identify as the pinned fork build (platterpus-fork-g9003e6f)"* — both
  rendered from the same run.
  - Cause: the headline came from `HostSetup.is_ready()` alone, which is
    `cyanrip_exported() and flac_exported()` — pure **reachability**. The user's
    *previous* fork build was still exported, so it answered `True` (correctly, to a
    different question), and the verdict never consulted the results list, so a
    `FAILED` step could not affect it. *"Can this check be satisfied by the wrong
    thing?"* — answered by shipping.
  - The failed steps now decide the headline. Tri-state, because two of the states
    are real: a user whose fork step failed but who has a working older ripper **can**
    rip, so "setup did not complete" would be as wrong as "setup complete". The
    message names both facts and the failing step's detail.
  - `setup_finished`'s payload deliberately stays reachability — its only listener
    asks "can I refresh the drive list now?", which is genuinely that question. The
    signal is now documented as such so the two are not conflated again.
  - **The gap that hid it:** the pre-existing failure test uses `ready=False`, where
    reachability and the results agree, so it could never catch this. A test that only
    exercises the case where two signals agree cannot detect that the wrong one is
    being read. `tests/test_ui_host_setup_dialog.py` now covers `ready=True` **with** a
    failed step, and was confirmed to fail against the old logic.

## [0.6.4b1] — 2026-08-04

**Beta, for the joint hardware test session.** This build exists to *produce* the
evidence handshake round 7 needs to close, and it says so about itself: it ships as a
GitHub pre-release, and every rip's report records
`ripper_handshake_approval: not_determined` or `unapproved` unless the installed
ripper is the build a closed round verified. **It is not a verified pair.**

Paired with the cyanrip fork's own beta — see `docs/handshake/verified/round-07-lap-07.md`
for the two builds by name.

### Fixed
- **A clean rip was told its command line had been tampered with.** The argv-agreement
  self-check compared the argv of the *last* ripper invocation against the `Invoked as:`
  line in the archival log, which is written by the *first* one. Any rip where the dynamic
  secure-rerip fired — i.e. any rip with an AccurateRip miss, the ones you look at closely —
  reported *"the command line changed in transit between Platterpus and cyanrip … Something
  between us (the host export wrapper, a shell) altered it"*, naming the auto-fix pass's
  `-Z` and `-l` as injected arguments. Nothing had altered anything. Found in a real
  14-track rip of *The Police — Every Breath You Take: The Classics* (2026-08-03).
  - The report now records `outcome.ripper_argv_first_pass` alongside `ripper_argv`, and the
    check compares like with like, naming which pass it covered. `null` when there was only
    one pass, so "single-pass" and "first of several" stay distinguishable.
  - A cross-check that accuses the user's system of tampering whenever the product's own
    self-heal fires is worse than no cross-check.
- **`outcome.failure_hint` was populated on successful rips.** A dynamic secure-rerip that
  does not converge on one track makes the ripper print `Done; (no matches found, but hit
  repeat limit of N)`, and that was scraped into a field named `failure_hint` on a rip whose
  status was `success` and whose exit code was `0` — telling every consumer, and
  `--audit-rips`, that this was why the rip failed. The hint is now recorded only on a
  non-success outcome; the read-stability fact still reaches the user through the EAC-style
  log's `Read stability` line and the warn banner, which is where it belongs.

- **The EAC-style log's `Defeat audio cache` row did not say where its answer came from.**
  The fork read it as an echo of cyanrip's own `Cache model:` line and asked us to stop
  claiming a cache verdict we could not know. The mechanism half of that was wrong — the row
  is a **measured** `cd-paranoia -A` probe of the real drive (KDD-29), and the parser is
  asserted never to fill the field from the ripper's log — but the presentation half was
  right: a bare `Yes` in an EAC-shaped log is indistinguishable from an asserted one, and a
  reader who cannot tell a measurement from a claim has been given a claim. The row now
  names its own method inline whenever a verdict exists.
- **An illustrated field inside a code fence was read as a declaration.** A handshake round
  file legitimately quotes the header format to explain it — and our parser read those examples
  as facts about the file itself. Our own lap-3 file adopted `PROVIDER-CONTRACT` from inside a
  fence, a field we are not even entitled to declare, and its verdict resolved correctly only
  because the illustrated value happened to match the real one. **Our test suite asserted the
  wrong behaviour outright**, with a confident comment about not parsing markdown. Fences are
  now stripped before matching; the assertion is inverted with the reason beside it. Found by
  the fork, on our file, after their gate compiled an illustrated `HANDSHAKE-PEER-VERSION` into
  their binary as a fact about us — three bait shapes now (indented, prose, fenced) and each
  project had found two of the three.
- **A timing gate that reddened CI at random.** `test_regex_bounded_time`'s detector-proof
  measured 10.9x growth on a *linear* pattern against an 8.0x ceiling — one run in three, in a
  container. Wall-clock noise (a GC pass, a scheduler hiccup, a co-tenant) can only ever make a
  measurement *longer*, so a single sample in the denominator inflates the ratio without bound.
  Now min-of-3, which is the standard reasoning for timing short operations. 5/5 stable at 29s
  for the file; a stable gate at 29s beats a flaky one at 10s, because a gate that fires at
  random is a gate people switch off.
- **`report_types.py` described half the report it calls itself the source of truth for.**
  Its docstring says *"single source of truth for the structure `rip_report` WRITES"*; it was
  missing **13 of 28** keys of the `rip` block and 4 of the `outcome` block — eight of them
  shipped in schema v13/v14, and one (`ripper_argv_first_pass`) was added earlier in this same
  cycle. A `TypedDict` that under-describes a dict literal is not a type error, because the
  emit site is not annotated as the `TypedDict`, so mypy had nothing to compare. All 17 are now
  declared and the two sets are diffed every commit
  (`tests/test_report_types_completeness.py`). Same expired-completeness pattern as the two
  documentation maps above, in code rather than prose.
- **The argv-agreement check was blind to a *long* option appearing in transit.** It
  compared single-letter flags only, so `--injected-by-a-wrapper` turning up in the ripper's
  `Invoked as:` line — the exact class of injection the check exists to catch — passed as
  agreement. Found by the new multi-pass test's own tamper case, not by review. Options are
  now compared short **and** long; values still are not, because `-s 667`'s `667` and
  argv[0]'s resolved path legitimately differ between what we spawn and what the ripper
  prints, and comparing those would cry wolf on every rip.
- **The release gate counted a deliberate `HOLD` as a closed handshake round.**
  `scripts/handshake.py --status` reported a round CLOSED when three files existed, and
  `--release-gate` is a thin wrapper over it. Round 7's verification file exists and declares
  **`HOLD`** — a mid-round lap, at the fork's own request — so the gate printed *"every round
  is closed — release allowed"* while the one rule the deviation policy states explicitly is
  *no release and no pin switch while a round is open*. The gate now reads the **verdict** the
  verification declares, not the file's existence: `GO` closes a round, `HOLD` does not, and a
  verification with no verdict at all fails closed. Rounds 1–3 predate the convention and are
  grandfathered by number in a list a test pins to exactly `{1, 2, 3}`, because "add the round
  to the exemption list" would otherwise be a one-line way to close an open round.
  - The marker is anchored to the start of a line on purpose. Round 7's own second paragraph
    says *"not a closing GO"*, and a matcher scanning anywhere in the text would have read
    that file as a GO — closing the round off a sentence saying the opposite.
  - This is the sibling of the round-6 finding in the same script, one function over: that fix
    went into `--check` and this defect was in `--status`. Fixing a detector where you found
    it leaves the flaw everywhere else in the file.
- **The argv-surface agreement test hard-failed when an inbound handshake round shipped no
  provider contract.** Round 7's file has no §I at all — genuinely absent, not relettered —
  and the test read the newest round unconditionally, so it found zero published flags and
  failed as though *our* argv had drifted. It now walks back to the newest round carrying at
  least 30 published flags and names which round it measured against, so a round that omits
  the table degrades to "checked against the last real one" rather than a false accusation.
  A missing contract is the fork's problem to fix; misattributing it to our argv is ours.

### Fixed
- **`MM:SS.FF` durations were read as hundredths, or not at all.** cyanrip prints two
  duration shapes and the fraction means different things in each: `HH:MM:SS.mmm` is
  milliseconds, `MM:SS.FF` is **CD frames** (1/75 s, 0–74). Our helper demanded the
  three-field form and returned nothing for the two-field one, so a disc duration was
  silently absent — and loosening the pattern without noticing the units would have made
  every per-track duration wrong by up to 0.98 s. `parse_cd_duration_to_seconds` now
  discriminates on colon count, as the ripper's published units block instructs, and
  **refuses** a frame field above 74 rather than reinterpreting it.
  - **The shape change is *upstream's*, not the fork's** — PR #130, which the fork
    inherited. Corrected after the fork pointed it out (round 7 lap 2 §1). It matters
    beyond attribution: *"roll back to stock cyanrip"* does not restore the old
    duration shape either, which is the second measured instance of the rule the `-V`
    removal taught — an upstream change cannot be escaped by rolling back to upstream.
  - Real hardware corrected an assumption in our own comment: the shape is not
    length-dependent. A 59:42 disc prints `Total time:     59:42.57` — two fields on a
    full-length disc, where we had guessed it would switch to `HH:MM:SS.mmm`.

### Changed
- **The pin a handshake round is *reviewing* is now recorded separately from the pin we
  build.** `deps/fork_source.py` gained `NEXT_PIN_UNDER_REVIEW` / `NEXT_VERSION_UNDER_REVIEW`,
  which name the fork commit an open round proposes without installing it. `FORK_PIN` stays
  at the last commit a **closed** round verified (`2f950c8`); round 7 proposes `d5d12ec` and
  it is deliberately not built. Written after the pin was moved to a round-7 commit here and
  the release-gate test caught it — the deviation policy forbids switching pins while a round
  is open, and until now there was nowhere to put the proposal except the pin itself.
- **The fork's expected version banner is single-sourced.** `FORK_EXPECTED_VERSION` /
  `FORK_EXPECTED_BANNER` in `deps/fork_source.py` are what the tests' stand-in ripper now
  prints, instead of three test files carrying their own copy of the version string. A
  stand-in that disagrees with the product about what the fork announces is a fixture testing
  itself.
- **The docs are consolidated: 79 markdown files → 64.** Content is preserved verbatim —
  each merged part is the original file, whole, with its headings demoted one level and a
  provenance table recording where it came from.
  - `docs/eac-parity.md` ← four EAC investigations (`eac-parity-investigation`,
    `log-format-comparison`, `eac-log-and-repair-feasibility`,
    `eac-tracker-requirements-2026-07`). They answered one question between them and now
    live in one place, Part A first because it carries the framing the others assume.
  - `docs/cyanrip-fork.md` ← `ripper-engine-strategy` + `cyanrip-soft-fork`: why we fork,
    and how the fork is kept sane.
  - `docs/cyanrip-upstream.md` ← `cyanrip-improvements-wanted` + `upstream-pr-roadmap`:
    what we want, and how it reaches upstream.
  - `output_reference/`: nine per-directory READMEs → one. Nine files describing one 3×3
    matrix meant the shared rules (no audio, UTF-16, how to replace a rip) were restated
    nine times and could drift nine ways.
  - `docs/audit-2026-07-21.md` → `docs/archive/`, where dated investigations belong.
  - **Parts are lettered, not numbered, deliberately:** the merged sources number their own
    sections from 0, so a numbered wrapper would make a cross-reference like *§2.1*
    ambiguous. Every inbound `§N` reference was rewritten to name its part — `Part A §8`
    reads exactly one way.
  - Deliberately *not* merged, with reasons: `manual-ctdb-repair.md` is a user runbook
    rather than an investigation; `ctdb-crc-algorithm.md` is a live spec cited from code;
    and `testing.md` / `test-plan.md` / `hardware-test-checklist.md` serve three different
    audiences, with `testing.md` anchored as the Definition of Done from `CLAUDE.md`.

### Added
- **Beta update channel — opt-in, with a warning (Settings → Updates).** *"we should be
  able to auto update to a beta release of platterpus and any dependencies, a warning
  should be given and an option, but for testing we need this."* A new
  **Offer beta (pre-release) updates** checkbox (`update_channel`, default `stable`)
  decides whether the update check considers pre-releases. Off, you only ever see
  finished releases. On, a beta offer **says in the dialog that it is a pre-release**
  and **"Yes" is not the default button** — a tester build never installs on an unread
  keypress. Documented in the in-app user guide.
- **`ForkTarget`: the wizard can install a nominated test build.** `--install-ripper`
  and the setup wizard now build `WIZARD_TARGET`, which for this beta is the fork's
  round-7 test pin (`9003e6f`, `cyanrip 0.9.4-rc1+platterpus.5-beta.1`) on the
  maintainer's instruction. `FORK_PIN` — the production record — is untouched, so a
  test install cannot become the approved pin by accident. `--install-ripper` prints,
  *before* minutes of dnf and meson, that every rip will report `unapproved` and that
  this is correct while the round is open.
- Rip-time handshake verification now explains a recognised-but-unapproved build instead
  of only naming it: the current test pin says it *is* a nominated test pin, a **retired**
  one says so and names the current one, and the pin under review says the round is open.
  The verdict is unchanged (`unapproved` either way) — only the sentence is, because "NOT
  the build this Platterpus was verified against" during a test session is the
  accurate-and-useless message this project keeps re-learning to avoid.
- `platterpus-fork-g9003e6f` accepts `--consumer`, so the beta's rig logs carry both
  halves of the pair instead of `Consumer: not identified`.

### Security
- **`cryptography` 48.0.1 → 50.0.0 (CVE-2026-69247).** The CI `pip-audit` gate went red
  with no change to our code, and the cause was the *ceiling*, not the floor: `49.0.0`
  carries the CVE, the fix is `50.0.0`, and our range was `>=48.0.1,<50` — so the ceiling
  **excluded the only fix** while pip-audit resolved the vulnerable top of the range. Now
  `>=50.0.0,<51` (pyproject) and `~=50.0` (AppImage), bumped together. Verified against
  50.0.0 before the bump: the Ed25519 verify surface `update_signing.py` actually uses,
  plus 32 signing/install tests.

### Fixed
- **The AppImage was being built from PyPI, not from the source tree.**
  `build/python-appimage/requirements.txt` carried a bare `platterpus`, and
  `--find-links` only *adds* a source — pip still picks the highest acceptable version,
  and **pip excludes pre-releases by default**. So the first `v0.6.4b1` release attempt
  built an AppImage containing **0.6.3** off PyPI, and the version sanity-check failed it.
  Invisible for every previous release because the tree version and the newest PyPI
  version were always the same number, so "built from the tree" and "built from PyPI"
  produced identical binaries — two witnesses agreeing because they share an ancestor.
  The build now pins the line to the exact wheel it just built (`platterpus==<version>`),
  which PyPI cannot satisfy, and restores the committed file on exit.
- **A second `trap … EXIT` in the build script would have orphaned the build stamp.**
  bash allows one handler per signal and a second `trap` silently replaces the first;
  both cleanups now run from one `cleanup` function.
- **A beta and its own final release compared equal, making the beta a one-way door.**
  The updater's version compare read `0.6.4b1` and `0.6.4` as the same `(0, 6, 4)` — so a
  tester on `0.6.4b1` would never have been offered `0.6.4`, or `0.6.4b2`. Release
  versions now sort PEP 440-aware: `0.6.3 < 0.6.4b1 < 0.6.4b2 < 0.6.4rc1 < 0.6.4`.
- **The update check offered whatever was newest by *publication time*.** A patch
  backported after a newer release would have been offered as an upgrade — i.e. a
  downgrade. Selection is now by version. Relatedly, one unparseable tag in the list no
  longer abandons the whole check (it used to report "couldn't check" with five valid
  releases sitting below the odd one).
- The `is_prerelease` decision reads the **version string**, not GitHub's `prerelease`
  flag: this project marks *every* `v0.*` tag as a pre-release, so for the entire 0.x
  line that flag is a constant. Gating the stable channel on it would have left stable
  users with nothing on their channel at all — caught by a test whose fixture is simply
  what our releases really look like.

### Tests
- `tests/test_handshake_approval.py` — the rip-time approval check shipped with **no test
  of its own**; the only thing touching it asserted the report *carried* the keys, not
  that the verdict in them was right.
- The wizard's build and verify steps can no longer be given different builds
  (`ForkTarget` is one object, asserted over *both* targets plus a non-triviality check
  that the two are distinct commits), and a nominated test pin must be named in the
  newest inbound handshake round — the check that catches a **retired** pin, which this
  round produced twice.
- The verify snippet gains the case the old two-constant design could not express: the
  *right fork* at the *wrong build* must fail.

### Added
- **A gate that every relative link between the project's docs resolves**
  (`tests/test_doc_links.py`). 79 markdown files cross-reference each other 200+ times and
  nothing checked that any of those pointers landed, which made renaming or merging a
  document a silent-breakage operation. Anchors are checked as far as the file, external
  URLs are skipped on purpose (a network check in a unit suite is a flake generator), and
  code fences are excluded so an illustrated link is not read as a real one. Carries a floor
  so it cannot pass by finding nothing.
- **T14 — the dynamic secure-rerip, tested end to end**
  (`tests/test_multi_pass_rip_end_to_end.py`). Both of this cycle's real user-facing bugs
  lived on the multi-pass path, both were found by a human reading a real rip's artifacts,
  and both were the same shape: a report describing a two-pass rip through fields that assume
  one pass. Every individual piece had unit tests; nothing walked pass 1 → AccurateRip miss →
  pass 2 → merged report, so the *seam* — where both defects were — had no coverage. The new
  test drives a real `RipWorker` over a two-call fake ripper, writes the report to disk,
  **re-reads it**, and runs the real audit over it. Offered to the cyanrip fork as T14,
  because their side has the mirror-image gap.
  - Floors first: it asserts the second pass actually ran, that the two argvs actually
    differ, and that the album log's `Invoked as:` is the whole-disc pass's. Without those, a
    fake that collapsed to one pass would make every downstream assertion pass while proving
    nothing.
  - And it asserts the fix did not simply switch the check off: the same clean rip with one
    argument injected must still be caught.
- **Gates for the two documentation maps that are declared canonical by prose.** Both had
  drifted, and both drifts were invisible in a diff because a map is only ever wrong by
  omission.
  - `tests/test_doc_index_completeness.py` — `CLAUDE.md` calls `docs/README.md` *"the
    canonical annotated index"* with a parenthetical saying the list *"can't drift from it
    again"*. That parenthetical was the entire enforcement, and it had already failed:
    `docs/cyanrip-consumer-contract.md` was listed in `CLAUDE.md` and absent from the index,
    and `docs/handshake/` — 24 files of binding release correspondence — was reachable from
    neither. The gate requires an *annotated row*, not a mention, because a document
    mentioned once in passing prose has a resolving link and is still lost.
  - `tests/test_planning_module_map.py` — `PLANNING.md` §2 opens *"one paragraph per
    module"*. It was missing **19 of 122 modules** from the directory tree, the responsibility
    list, or both — including `hard_exit.py` and `ripper_identity.py`, which `CLAUDE.md`'s own
    Critical rules and Code conventions name by name. All 19 are now documented, and the map
    is swept against the filesystem every commit.
- **Handshake protocol v2, and the spec is now one shared file instead of two descriptions.**
  Our lap 3 wrote its own §8 saying *"one language, both repos"* — and thereby created a second
  copy of the spec, which is the two-vocabularies problem in miniature. The fork wrote it up as
  a standalone document; we adopted that verbatim as `docs/handshake-protocol.md`, and
  `docs/cyanrip-handshake.md` §8 now routes to it rather than restating it.
  - **`HANDSHAKE-PROTOCOL` is required, and a higher version than we implement is refused**
    rather than guessed at — a v2 gate cannot know which of v3's rules it is silently not
    applying, including a new close requirement.
  - **A close now requires the fork's field set too:** both verdicts, both versions, both pins,
    and `HANDSHAKE-TESTED`. The last is the maintainer's *"proper testing is needed"* as a
    field — a round that closed with nothing tested is a release nobody checked. `--check`
    reports a `GO` that cannot close *at check time*, naming the missing field, so the author
    learns while they are still writing it.
  - **A field declared twice is ambiguous, not "the last one".**
- **`tests/test_handshake_conformance.py` — the shared protocol's 14-row conformance table, one
  test per row, run against our gate.** It found a real defect on the first pass: **row 12, an
  empty record, allowed a release.** `round_status()` returned a bare "no handshake rounds"
  line; the gate decided by looking for lines ending in `OPEN`; that line did not; therefore
  nothing was open. *A gate satisfied by finding nothing, in the gate whose entire job is not
  being satisfied by nothing.* Row 14 (a complete round must be **allowed**) is asserted first
  in the file, because a gate that can never say yes passes every refusal row.
- **The cyanrip handshake is now affirmative, bilateral, and checked at the drive**
  (maintainer directive). Four parts, each previously enforced somewhere other than where it
  mattered:
  - **Both sides must declare `GO`.** `--status` read *our* verdict and not theirs, so the
    fork's `HOLD` could not block our release — one half of a two-half contract, for the third
    time in this protocol's life. A round is CLOSED only when both verdicts are `GO`; four
    combinations are tested, and only that one closes.
  - **One wire format, both repos.** Both projects built a release gate within a day of each
    other, to the same four properties, in two different vocabularies: ours read bolded prose,
    theirs read `HANDSHAKE-VERDICT:` headers, and neither could read the other's files.
    Theirs wins on the merits and is adopted — machine-readable, survives rewording, and a
    round number *in* the file cannot silently disagree with the filename. Specified in
    `docs/cyanrip-handshake.md` §8 and reproduced verbatim in every round file, because the
    fork does not have this repo and "see §8" is a pointer into a tree they cannot read.
  - **Both versions named.** `HANDSHAKE-APP-VERSION` and `HANDSHAKE-RIPPER-VERSION` are
    required fields: a round approves a pin *for a named app version*, and two artifacts from
    the same ripper under different app versions are not interchangeable evidence.
  - **Every rip verifies its own ripper** (`handshake_approval.py`, report schema **v15**). A
    release gate runs once on a machine that never rips a disc; the rig is where an unapproved
    binary would actually be used. Tri-state — `not_determined` is not a pass, and an
    unrecognised build tag is never reported as unapproved. The rip that ran an
    under-review pin says so, by name, in its own archived report.
- **A mid-round lap is no longer held to the full ten-section list.** Our checker reported 20
  problems against the fork's lap-2 reply, which legitimately has no golden log and no commit
  table because nothing about those changed in that exchange. `HANDSHAKE-LAP` makes it
  decidable rather than a judgement: lap 1 is a full round file and is swept, lap ≥ 2 is a
  reply and is not. Over-strictness is the failure whose usual fix is switching the checker
  off.
- **Section F of the hardware checklist: the three artifacts we owe the cyanrip fork**, each
  written so it can be run without re-deriving anything. Round 7 cannot close without them and
  neither project releases while it is open, so they are now near the top of the
  if-you-only-have-an-hour list rather than three lines in `TASKS.md`. F3 (the forced-error
  corpus) is five one-line commands, needs no disc for the first, and writes nothing — and it
  is deliberately *not* hand-assembled here, because a corpus built from my reading of their
  control flow is a fixture carrying my assumptions about their control flow.
- **Readiness tests for the shapes the fork's next handshake file can arrive in** — an
  amendment to the open round, or a fresh round opened out of order. Both are legitimate and
  the machinery now handles each without a human deciding which; the last two rounds each
  surprised the tooling once. Includes a test that reads the committed round-7 file and
  asserts `--check` still names its absent §I, so when they supply it, the test is what
  confirms it rather than my reading the file and forming an opinion.
- **A behavioural test that the rip log is read only after the ripper is reaped.** cyanrip's
  logfile was block-buffered, so a killed process lost up to a 4096-byte stdio block — the
  round-1 finding, reproduced against a real cancelled rip whose log ended mid-token at
  `REPLAYGAIN_TRACK_GA`. The fork's `setvbuf` fixed the source; our half is ordering, which
  was correct and untested. The fake writes the log from inside `wait()`, so an inverted order
  finds nothing — verified by inverting it.
- **`docs/handshake/README.md` is now a round-by-round map**, and gated. It described the
  closing rule as *"all three files exist"* — the rule that was wrong — and named exactly one
  round, four rounds in. Two tests now derive the expected rounds from the directories and
  assert the file does not teach the superseded rule.

## [0.6.3] — 2026-08-03

### Added
- **`platterpus --install-ripper`** — set up or update the ripping stack from the terminal and exit:
  the Distrobox container, cyanrip, and the pinned Platterpus fork of cyanrip built over it, then
  re-point the host export at the fork. Idempotent; prints each step as it lands, plus the pin it is
  building and the build tag the finished binary must report.
  - Why it exists: the pin lives inside a Platterpus release, so a user on an older build had **no
    in-app route to a newer ripper**. The fork's pin moved three times in one day (`e1d800e` →
    `ad65a24` → `25a2265` → `2f950c8`), which makes the release cycle the wrong granularity. It
    drives the *same step engine* as the GUI wizard rather than a documented shell snippet — a
    second description of the install would drift the first time a build dependency changed.
  - Its verdict keys on the ripper being usable, not on every step passing: `cd-paranoia` is
    optional and deliberately last, so an unmeasured cache verdict does not read as "not installed".

### Changed
- **The pinned cyanrip fork moves to `2f950c8` (fork release r2)**, closing handshake round 6.
  `ad65a24` — which round 6 asked for — is **superseded and must not be built**: at that commit,
  ripping a BIN/CUE, NRG or cdrdao *disc image* at any paranoia level above 0 returned one correct
  sector followed by silence, 99.7% of samples zeroed, reported as `Ripping errors: 0`. The defect
  is inherited from upstream (`c431d58` set paranoia's cachemodel — which doubles as its `c_block`
  read-chunk size — to 1 sector for image drivers), so every earlier fork build and stock upstream
  carry it equally.
  - **No disc ripped on real hardware is affected.** The override applies only to the three
    image drivers; a `/dev/sr0` rip never enters it. Verified from the fork's source, and against
    our own committed references — `output_reference/cyanrip_*` are real-drive rips, and both
    committed golden references were generated with `-P 0`, which was always byte-perfect.
  - Verified independently rather than accepted: the cause commit, the fix's diff and its driver
    scoping, and — because the reference's own build tag names a commit *below* the fix — that the
    fix is present in the binary that produced it, derived from the paranoia read-chunk counts in
    the log itself (`ceil(frames/16)` where the broken build logged one read per sector).
- **The fork's two log-line renames are handled with no behaviour change:** `Peak level:` →
  `Sample peak level:` (all three spellings the fork has used now parse) and `Cache defeat:` →
  `Cache model:`. The latter is deliberately *not* wired to our cache-defeat field: cyanrip reports
  what libcdio-paranoia **models**, our row is a **measured** `cd-paranoia -A` verdict (KDD-29), and
  filling a measured field from a model is the fabricated "Yes" KDD-25 forbids.
- `Encoder:`, `CD-TEXT:` and `Cache model:` are on the parser's documented ignore list with recorded
  reasons rather than silently unrecognised — candidates awaiting a report field, not drops.

### Fixed
- **The handshake checker (`scripts/handshake.py --check`) passed two absent sections and credited a
  third to prose.** It reported one problem in the fork's round-6 file; there were three. §G
  ("Revert-proof") was satisfied by an unrelated section they had lettered `## G. Asks back` while
  the word "revert" appeared zero times; §B's provenance markers were absent; and §I ("Provider
  contract") matched the sentence *"I wrote, of your continuation-line sweep:"* — the contract really
  was in the file, so the verdict was right and the reason was not, and it would have passed with the
  contract deleted. A check that passes for the wrong reason is worse than one that fails: a failure
  gets investigated, a pass gets cited.
  - A section key must now appear in a real heading position (`#`, `**` or `§` — a bare letter at
    line start no longer counts) **and** the section's subject must appear in the document. Rounds 4
    and 5 still pass unchanged. `--check` also accepts several files, so a round delivered as a
    return plus an amendment validates as one round; and an amendment (`round-6b.md`) belongs to its
    round rather than counting as one, so sending a correction within hours no longer scores worse in
    the record than folding it into the next round.
- **The per-track paranoia counters are per-*pass*, and the disc total is not their sum.** Round 5
  of the handshake told us they sum exactly, and we verified it — on an artifact ripped without `-Z`,
  where the sum is arithmetically forced. Read from the fork's source, the per-track baseline is
  re-snapshotted inside the `repeat_ripping:` loop, so the per-track figure is the final pass and the
  disc-level tally is every pass: a `SKIP: 300` on a `-Z 2` rip is three passes' worth of skips, and
  rendering it as 300 distinct events over-reports by the re-read factor. Documented next to the
  field with the citation, and pinned by a test asserting the sums *differ* so nobody later "fixes"
  the discrepancy into a false invariant.
- **The album-loudness block was gated on FFmpeg's wording, not cyanrip's.** The parser required
  the header `Album Loudness Summary:`; only `Album Loudness` is cyanrip's — the ` Summary:` tail
  comes from FFmpeg's `ebur128` filter, which the fork's contract explicitly marks as libavfilter
  wording that "moves when FFmpeg does". One upstream rewording would have emptied the whole
  `album_loudness` block silently. Found by diffing their round-5 unstable-line list against our
  patterns.
- **13 of the ripper's own error messages were never shown to the user** — each rendered as a
  bare "Rip failed." Two are ordinary hardware failures: `Offset is unset! To continue with an
  offset of 0, run with -s 0!` and `Device does not support changing speeds!`
  - The standing test asserting we surface everything the ripper can say was **green throughout**,
    because the fixture it asserted against was the cyanrip fork's machine-generated inventory
    *filtered through a hand-maintained 21-word prefix allowlist on their side*. Their round-5
    re-derivation from control flow took that inventory from 88 strings to 104; re-derived
    independently here at both pins, 104 each time, a strict superset with nothing lost. The
    fixture had inherited their filter's blind spot, so it measured their allowlist rather than
    the ripper.
  - The matcher is no longer a list of opening words. Each of the ripper's published `printf`
    formats is compiled into a pattern, so a line is a diagnostic because the ripper's own
    inventory says that text exists. 103 of 104 formats covered, 0 false positives on ordinary
    output; the one exclusion is a bare `%s`, which would match every line and is refused,
    named and asserted rather than skipped. The word prefixes survive as the forward-tolerance
    half for builds newer than the contract — never as the completeness half.
  - The provider's **evidence** column is preserved rather than flattened: 73 of the 104 are
    proven reachable on a failure path without reference to wording, and only that subset is
    safe for hard failure classification. All 104 are used for *surfacing*, because a message
    that turns out to be a warning is still more useful than silence.

- **RELEASE BLOCKER, found before it shipped: installing the fork would have made Platterpus
  report cyanrip *missing*.** Every version probe sent `cyanrip -V`. That is right for 0.9.3 and
  earlier — a short-only `getopt` with a `case 'V':` — and wrong for everything after: upstream
  commit `442de2a` replaced the parser with a generic one that accepts only `-v`/`--version` and
  rejects `-V` as an unparseable argument, exiting 1. A non-zero exit from a version probe is
  deliberately read as "this tool is not available", so the launch dependency check would have
  reported the ripper missing *immediately after the wizard successfully built it*, and the
  wizard's own post-install verification would have failed on a perfect build.
  - Probing now tries `-V` then `--version` — the minimal set that covers 0.9.3, stock 0.9.4 and
    the fork, with the field-proven flag first so the common case still costs one process and an
    unrecognised flag is never the first thing handed to a CD ripper. The flag list lives in one
    module (`cyanrip_cli.py`) that all four call sites and the wizard's in-container shell snippet
    read, so the shell and the Python cannot disagree.
  - **Not a fork regression** — it would have hit stock upstream 0.9.4 identically, which means
    "roll back to stock" was never an escape hatch for it. The fork has since restored `-V` as a
    compatibility alias, and we keep probing both anyway: that fixes their binaries, not the 0.9.3
    installs users have today.
  - The expected first failure is no longer logged as a conclusion. It used to emit
    "treating the tool as unavailable" per attempt, which on every fork install would have put an
    alarming and untrue line in the user's log; the absence is now logged once, where it is known.

### Added
- **The one-time setup wizard now installs the pinned Platterpus fork of cyanrip**, so using the
  fork no longer requires a terminal (KDD-17's zero-terminal bar, in the one place it mattered
  most). A new `cyanrip_fork` step installs the build dependencies, clones the fork, detaches
  onto the handshake-verified commit, compiles it, installs it to `/usr/local/bin/cyanrip`,
  re-points the `~/.local/bin` export at it, and then **verifies the installed binary prints the
  pinned fork's build tag** — an install that produced something unexpected fails the step
  loudly instead of leaving a mystery binary on the ripping path. It runs *after* the stock COPR
  install and export, so a failed build leaves a working ripper rather than none.
  The pin, the repo, the branch and the measured build-dependency list live in one module
  (`deps/fork_source.py`), and a test reads the newest closed handshake round to assert the code
  builds the commit the record approved.
- **The dependency check now names which *build* of cyanrip is installed**, not only its version.
  A wrong build is counted in the summary's headline, described in its own "Wrong build" block
  with what the difference costs and how to fix it, and shown with a warning icon rather than an
  information one. Tri-state, like everywhere else — an unrecognised build tag reports "not
  identified", never "unmodified upstream". Classification delegates to the shared
  `ripper_identity` module, so the dialog, the EAC-style log, the JSON report and `--doctor`
  cannot describe the same binary four different ways.

### Fixed
- **The launch-time dependency dialog said "cyanrip 0.9.3" and "0 missing/needs-attention" while
  the ripper was unmodified upstream, not the Platterpus fork.** Every word was true and the
  message was misleading: the fork keeps upstream's version string *deliberately* (its
  `meson.build` sets a separate `PROJECT_FORK_ID`), so a version number is the one fact that
  cannot distinguish the two. Platterpus had already been taught to name the build in the
  archival log, the report and `--doctor`; this was the surface a user actually reads at launch,
  and it had been missed. Found by the maintainer reading the dialog.
- **A multi-disc rip wrote `DISCNUMBER=2/3` into its FLAC files** — the ID3 convention, not the
  Vorbis one — and dropped the disc total entirely. The disc position was folded into cyanrip's
  `-a` album-tag string as `disc=2/3`, which ffmpeg's Vorbis-comment writer passes through
  verbatim under the mapped key `DISCNUMBER`. It now goes through cyanrip's own
  `-c disc/totaldiscs` flag, which parses the slash and sets `disc` and `totaldiscs` as separate
  integer keys. Single-disc releases get `1/1` too, matching what EAC and Picard write, so the
  field does not appear only on box sets. Found by diffing our FLAC tags against an EAC baseline
  on real hardware.
  - The value is **range-checked at the argv chokepoint**, because cyanrip refuses the *entire
    rip* on a bad `-c` (`Invalid discnumber`, `Invalid totaldiscs`, `discnumber N is larger than
    totaldiscs M` — all exit 1 before a sector is read). Same defect shape as the out-of-range
    `-t` that killed a real rip in two seconds. An unusable disc position is dropped and logged;
    losing a tag is survivable, losing the rip is not.
- **Four audit checks could run and say nothing**, which in the report is indistinguishable from
  a check that found everything in order. The first real-hardware run of the embedded
  `self_check` listed eight checks run, zero skipped, and carried six findings — `pregap` and
  `argv_agreement` were silent because stock cyanrip emits neither the rows nor the
  `Invoked as:` line they read; auditing for it found `medium` and `log_integrity` too. Each now
  reports *why* it has nothing, and `run_checks` carries a structural floor so a future silent
  check is impossible rather than merely discouraged.
- **`self_check`'s verdict could never read "ok"** for a flawless rip: recording the disc's
  identity was a check that *succeeded* but was graded as a note. A grade that is always at
  least "note" is not a verdict.

## [0.6.2] — 2026-08-02

### Added
- **Three more automatic checks**, in the same registry so they land in every rip's `self_check`
  block *and* in `--audit-rips` at once:
  - **Did the ripper receive the command line we sent?** Both halves of this comparison already
    existed and nothing compared them — we record the argv we spawned, and the fork prints the
    argv it received (our handshake ask A3). The pair exists precisely so that a wrapper, a
    shell, or the Distrobox host-export altering an argument becomes visible, and a difference
    nothing looks at is not visible. Compared as sets of flags, not strings: the ripper's
    `argv[0]` is the resolved path behind the export while ours is the wrapper, so a string
    compare would cry wolf on every rip.
  - **Does the EAC log still match its own SHA-256 footer?** We publish that checksum as an
    openly-verifiable integrity claim (KDD-28); publishing a claim and never checking it is the
    weaker half of a promise. Tri-state — a log with no footer is reported as having none, not
    as having passed.
  - **The TOC-derived disc identity** (MusicBrainz Disc ID + CDDB ID), so two rips of the same
    pressing can be compared without opening the JSON by hand.

## [0.6.1] — 2026-08-02

### Fixed
- **The README still announced "Status: v0.5.x" deep into the v0.6 line**, and `SECURITY.md`
  still said only `v0.5.x` was supported. The doc-stamp gate could not catch either: a stamp
  records *when a doc was last edited*, so a doc nobody edits keeps an accurate stamp while its
  prose quietly expires. Those are two different properties and now have two different checks —
  `tests/test_no_stale_version_claims.py` fails both on a doc claiming an old version **and** on
  a `__version__` bump whose CHANGELOG section, compare links, README banner or SECURITY line
  have not followed.

### Added
- The in-app **User Guide** covers the v0.6.1 behaviour: which cyanrip built a rip and where to
  see it, `--audit-rips`, the `self_check` block in every report, the multi-disc "could not
  determine" warning, and — the confusing one — why a cancelled rip legitimately leaves 0-byte
  audio files. `--audit-rips` is in the README's command-line section, and a test derives the
  flag list from `app.py` so a new flag cannot ship undocumented.

### Added
- **Every rip now audits itself, and the result is in the JSON.** A `self_check` block records
  which cyanrip built the rip, whether the ripper said it finished, which disc of a multi-disc
  set the tags came from, what pre-gap provenance was observed, and **whether the audio files
  the log claims actually have bytes in them** — the last one made necessary by the fork's
  measurement that a killed rip leaves 0-byte FLACs for tracks its log reports complete. Checks
  live in one registry, so adding a future one is a single function plus a row, and it appears
  in both the per-rip block and the bulk audit at once. A check that cannot run is recorded as
  **skipped and named**, never silently omitted.
- **`platterpus --audit-rips FOLDER`** — the same checks over a whole library, in one command,
  read-only. Replaces a hardware checklist that asked a human to open files and read fields.
  Exits non-zero when something needs attention.

### Fixed
- **`rip_completed` and `invoked_as` were parsed and never serialized**, so the report said the
  ripper's completion footer was absent for logs that plainly had one. Found by the embedded
  self-check the first time it ran — which is the argument for having a consumer. Schema **v14**.

### Fixed
- **A cancelled rip's own track counts were dropped.** cyanrip's footer has two shapes, and only
  one was handled: `Rip completed: yes (3 of 3 tracks)` parsed, while
  `Rip completed: no (interrupted by user, 2 of 3 tracks)` matched the verdict and **silently
  lost "2 of 3"** — the ripper's own count, for exactly the scenario where our own count is
  least trustworthy. No fixture could have caught it (their golden reference is a *successful*
  rip); it came out of the fork's generated provider contract. The interruption reason is now
  kept verbatim too, rather than inferred from the boolean.

### Added
- `tests/test_provider_contract_agreement.py` — a standing check that **we parse nothing the
  fork reserves the right to reword**. Their P3 list is text they may change without a
  handshake; parsing one of those means their next cosmetic edit breaks us silently. Currently
  zero overlap. Also pins the four log variants that exist in their contract and in no artifact
  we hold: the CRC-mismatch pre-gap, the lead-in-sourced pre-gap, the sub-channel source, and
  the cancelled footer.

### Documentation
- cyanrip handshake **round 4 is closed in both directions** — their return file verified
  claim-by-claim against the real parser and the committed fixtures, and our verification sent.
  `scripts/handshake.py --status` reads all four rounds CLOSED. The release gate is now the two
  honestly-outstanding hardware items (a successful sub-channel pre-gap read, and a cancelled
  rip against the new pin), not anything unresolved between the projects.

### Added
- **`--doctor` now says which cyanrip build the container has** — "the Platterpus fork",
  "unmodified upstream", or "build not identified" — so the question *"am I on the fork?"* is
  answered before a disc is committed to a rip rather than discovered from the log afterwards.
  A separate check from reachability, because a container that works but has the wrong build
  needs a different sentence from a broken one. Never a FAIL: upstream cyanrip rips perfectly,
  it just cannot fill the archival rows the fork can.

### Added
- **The ripper's `Invoked as:` line is parsed** (cyanrip fork round 4, our ask A3). We already
  record the argv we *spawned* it with; this is the argv it reports *receiving*. The value is
  entirely in the difference — a wrapper, a shell, or the Distrobox host-export mangling an
  argument is invisible from either end alone.
- **`Rip completed: yes (N of M tracks)` is parsed**, tri-state. The ripper's own completion
  verdict with its own denominator, and per the fork the only structural difference between a
  truncated log and a short one (the cue cannot tell). `None` means the footer was absent —
  what a killed rip looks like — and is never read as `False`.
- `tests/fixtures/cyanrip_fatal_messages.tsv` — the fork's mechanically generated inventory of
  all 88 strings it can print on a fatal path, committed so our surfacing pattern is tested
  against the ripper's real vocabulary rather than strings we imagined. Coverage re-measured
  independently at 87/88, the miss closed, now **88/88**.

### Fixed
- **`Total time:` was silently unparsed on short discs.** The pattern demanded `HH:MM:SS`;
  cyanrip prints `MM:SS.ff` for a short disc, so the fork's own golden reference fell through
  as an unrecognised line and the disc duration went missing. Found by running the parser over
  the round-4 fixture, not by reading it.
- `-J (only generate a CUE sheet) cannot be used with -I` — the one fatal string no word prefix
  could reach, because it starts with a hyphen.

### Added
- **`-N` is now enforced at the argv chokepoint, not merely documented.** Critical rule #5 says
  cyanrip must never run its own MusicBrainz lookup — without `-N` it reaches the network from
  inside the container and, on an ambiguous disc, opens an interactive prompt that has nowhere
  to appear, hanging the rip until the user cancels. `assert_metadata_lookup_disabled` is
  extracted so something can actually call it with a bad argv; a guard that cannot be exercised
  is a guard nobody has tested.
- The report's `disc` block records **which medium** of a multi-disc release the tags came from
  and how it was decided (`medium_basis` / `medium_detail` / `medium_undetermined`), so a rip we
  could not resolve says so instead of presenting the titles as settled.
- `docs/handshake/` — the full cyanrip correspondence record, both directions, rounds 1–4, with
  `verified/` entries closing rounds 1–3. Round 3's verification was late and went out folded
  into round 4; that is stated in the record rather than tidied away.

### Fixed
- **A multi-disc release could be ripped with the wrong disc's track titles.** Every code path
  took MusicBrainz's `medium-list[0]`, under a comment reading *"the first medium is the one we
  want in nearly all cases"*. On a four-disc set that meant disc 1's 18 tracks for a 16-track
  disc — the `-t 17=` failure that ended a rig rip. The argv chokepoint already stopped that
  symptom, and stopping it made the underlying bug **more** dangerous: suppress the two bad
  arguments and the other sixteen still go through, producing a complete, successful-looking
  album of wrong metadata. `medium_select.py` now picks the medium by **disc ID** (authoritative
  — ours comes from the physical TOC), then by a **unique** track-count match, then by there
  being only one medium. Two media with the same count is an *ambiguity*, not a match: the
  selector reports "not determined" with the counts it saw rather than flipping a coin and
  presenting it as a fact. The release fetch now requests MusicBrainz's `discids` include, which
  is what makes the authoritative match possible at all.

### Added
- **The cyanrip handshake protocol is now executable, in both directions.** It was prose, and a
  round arrived missing a required section twice. `scripts/handshake.py --emit N` builds our
  outbound file with every required section and renders the inbound spec from the same list the
  checker enforces; `--check FILE` validates a received one and exits non-zero listing what is
  absent, including the two failures worse than a missing section (present-but-empty, and a
  null case left silent); `--status` reports every round OPEN or CLOSED off `docs/handshake/`.
  It found two real gaps on first run, both ours: round 3 was never verified back to the fork,
  and the return spec had grown from A–I to A–J without being announced.
- `CLAUDE.md` **Critical rule #12** makes all of it standing behaviour — both contracts
  published, both directions enforced by tooling, full error capture always surfaced, the fork
  identified tri-state, and the rule itself mirrored into the fork's repo.

### Documentation
- `CLAUDE.md` gains three rules this round earned: *answer from the artifact, not your memory of
  it* (and give a correction from another project the same scrutiny as a claim); **diagnostic
  completeness** — exit code, exact argv, and complete output for every external tool, with
  head-and-tail bounding and a counted elision marker, because a silent truncation reads as
  completeness; and *say which build produced an artifact*, tri-state.

### Fixed
- **21 of cyanrip's 45 fatal messages were captured and never shown.** The fatal-line pattern
  matched six prefixes; the fork session enumerated the ripper's fatal log call sites and
  measured the coverage at 24 of 45. For the rest the report's `failure_hint` stayed `null` and
  the window said "Rip failed" while the ripper's own diagnosis sat in a buffer we had already
  captured. The pattern now covers 23 prefixes with a real word boundary (so `Invalid` still
  does not match `Invalidated`) and a punctuation-aware one (so `Out of memory!` matches at
  all). Narrowness was the wrong instinct: a miss costs a user the answer, a false positive
  costs one extra sentence on a rip that already failed.

### Added
- **Every rip now records WHICH cyanrip binary produced it.** Platterpus runs a fork that emits
  rows stock cyanrip does not (per-track pre-gap length and provenance, sample peak, extraction
  speed and elapsed time), so two logs of one disc from the two binaries are not interchangeable
  evidence — and the version number cannot tell them apart, because the fork tracks upstream
  versions. The EAC-style log gains an unconditional `Ripper build:` row and the JSON gains
  `ripper_is_platterpus_fork` / `ripper_identity` / `ripper_identity_detail` (schema **v13**).
  The verdict is **tri-state**: an unrecognised or absent build tag reports `unknown` / `null`,
  never "unmodified upstream", because that would be a claim we have no evidence for.
- **The ripper's exit code and exact command line are in the report.** Both were computed and
  discarded, so `1` (the ripper refused an argument), `0` plus a cancel (the user stopped a
  healthy run) and `-9` (we SIGKILLed a wedged process group) all rendered identically, and no
  report carried the argv needed to reproduce a failure by hand. `outcome.ripper_exit_code`,
  `outcome.ripper_argv` and `outcome.ripper_command_display`; a never-reaped child records
  `null`, not `0`.

### Fixed
- **A runaway rip dropped the ripper's dying message.** Retained stdout stopped at a 20 000-line
  cap, head-only — reasoned as "the head holds the header and the earliest tracks", which is
  true of a rip that succeeds and exactly wrong for one that fails, since a ripper's fatal line
  is the *last* thing it prints. Capture is now head **and** a rolling tail, with an explicit
  `[platterpus] … N lines … elided` marker naming how many lines went: an unmarked gap would
  read as a ripper that fell silent, which is a different and more alarming fact.

### Fixed
- **The EAC `Pre-gap length` row briefly stopped matching EAC.** A cross-project correction
  argued that EAC derives the row from `INDEX 00 → INDEX 01` only, so the fork's track-1
  `Pregap length: 300` (lead-in 150 + declared TOC gap 150) was not comparable; the row was
  switched to the subtraction, then switched back the same day. The committed EAC baseline
  prints `Track 1 … Pre-gap length  0:00:02.00` — the bare lead-in on a disc declaring no
  track-1 gap — so EAC's row *is* lead-in plus declared gap, and the fork's stated figure is
  the EAC-comparable one. No released version carried the wrong value.

### Added
- **`docs/cyanrip-consumer-contract.md`, generated from the code.** Every log line Platterpus
  parses, every line it knowingly ignores with the recorded reason, and every flag it passes —
  read out of the parser's enumeration tables and out of a real call to the argv builder, not
  written down beside them. It is the consumer half of the cyanrip dependency contract; the
  fork supplies the mirroring provider half. `scripts/emit_dependency_contract.py` regenerates
  it and `--check` fails on drift.

### Fixed
- **The track list could not be scrolled while a rip was running.** The rip lock called
  `setEnabled(False)` on the table to stop mid-rip edits; a disabled `QTableView` also ignores
  the wheel and the arrow keys, so for the entire rip the user could not scroll the one widget
  showing live per-track status. It is now locked **read-only** — every row stays legible,
  selectable and scrollable, while edits and Rip? toggles are refused at the model.

### Fixed
- **An out-of-range track tag killed an entire rip.** Disc 1 of a 4-disc set has 16 tracks; the
  MusicBrainz medium we used listed 18; Platterpus passed cyanrip `-t 17=` and `-t 18=`. cyanrip
  answered `Invalid track number 17, list has 16 tracks!` and exited — **two seconds, nothing
  ripped** (rig, 2026-08-02). `_metadata_args` now refuses to emit a `-t` for a track the disc
  does not have. That is the argv chokepoint, so the guard holds regardless of which path
  assembled the metadata — including the medium-selection defect that produced the bad list,
  which is still open.
- **The ripper diagnosed the failure precisely and the user was shown "Rip failed."**
  `failure_hint` was `null` while cyanrip's own sentence sat in the captured output. Its fatal
  argument/setup errors are now surfaced verbatim when we have no more specific hint.

### Documentation
- `docs/dependency-contracts.md` gains cyanrip's **argument range constraints** — the seven
  flags whose values it validates against the disc and exits on, with the `-t` row marked as
  measured rather than read.
- `docs/testing.md` §5.u — *answer it from the artifact, not from your memory of the artifact*.
  The pre-gap convention flipped twice in one day because a true count of `INDEX 00` lines in
  EAC's **cue** was cited as evidence about EAC's **log**. `tests/test_eac_pregap_convention.py`
  now derives the whole convention — truncated hundredths, the per-track formula, track 1's
  lead-in, and byte-exact reproduction of all ten real rows — from the committed artifacts, so
  it cannot flip again on anyone's recollection.
- `docs/cyanrip-handshake.md` — the "who was wrong" table gains that entry and the §H2 one, and
  the shared rigour bar gains two rules: cite the artifact, and give a *correction* from the
  other side the same scrutiny as a claim.
- `docs/testing.md` §5.m — *two rules already existed, neither ran*. Both halves of the above
  were written policy with no test, sweep, or chokepoint enforcing them. The graduated lesson
  is that a prose rule becomes real only when something executes it, and CLAUDE.md's
  validate-outputs rule now says so explicitly and names range as well as syntax.

### Fixed
- **A cancelled rip reported the disc *fraction* as a *rate*.** `realtime_multiplier` was
  `elapsed ÷ disc_seconds` regardless of whether the rip finished, so the rig's 2-of-14 cancel
  archived `0.21` (755 s of a 3582 s disc) when actual throughput was about 0.93×. A plausible
  wrong number is worse than none, because nothing about it invites checking. It is now `null`
  with a `realtime_multiplier_basis` saying why, or — when the log carries enough geometry to
  know how much audio *was* extracted — a real rate computed from that. The timing enrichment
  in the window now **delegates** to `build_timing` instead of recomputing the division itself;
  that second copy of the arithmetic is how the two got to disagree.
  A **failed** rip counts as not-completed too: gating on the cancel flag alone left that case
  open, and the rig found it the same day — a rip that died after 2 seconds on a bad argument,
  having read nothing, archived `realtime_multiplier: 0.0`.

### Fixed
- **`Pregap LSN: unknown` was indistinguishable from `Pregap LSN: none`.** The cyanrip fork
  prints `unknown (sub-channel unreadable)` when it tried a Q-subchannel scan and could not
  tell; our pattern was `(\d+|none)`, which matched neither `unknown` form, so the row fell
  through and the track came out byte-identical to a measured "no pre-gap". "We could not
  determine whether this track has a pre-gap" and "this track has no pre-gap" are different
  archival claims and the log is SHA-256 signed. Third instance of this class after
  `Accurip: disabled` reading as "in DB, no match" and the all-zero CRC counting as a match,
  so the fix is a **state** rather than another special case: `pregap_state` is one of
  `known` / `none` / `unknown`, with the reason recorded, and the EAC row now reads
  *"(not determined by the ripper — sub-channel unreadable)"* instead of vanishing.

### Added
- **`Pregap length:` and `Pregap source:` are read, and the stated length wins over our
  derivation.** `Pregap length` is the only field that can express track 1, whose gap is the
  150-frame lead-in *plus* any declared gap — the fork's reference disc reads `Pregap LSN: 0`
  / `Start LSN: 150` / `Pregap length: 300`, and its `Gaps:` block confirms a 150-frame TOC
  pre-gap, so 150 + 150 = 300 while subtracting gets 150. Our rendered rows now match
  cyanrip's own `(duration: …)` suffix exactly on both fork tracks. `pregap_source`
  (`TOC` / `lead-in` / `sub-channel`) is provenance we previously had to infer — a
  `sub-channel` value means a gap the TOC does *not* declare, which is the whole point of
  upstream PR #115. All four fields serialize into the JSON report; stock cyanrip is
  unaffected (all 14 reference tracks still measure `none` and render no row).

### Added
- **The ripper's own stdout is now embedded in the JSON report**, beside the three files
  (schema v12's `artifacts` gains `ripper_stdout`). This is the one record that survives the
  ripper being killed: cyanrip's logfile is block-buffered, its stdout is a pipe we are already
  draining. On the rig the logfile lost a track verified at AccurateRip confidence 200 while the
  stdout had it the whole time. Progress redraws are excluded (~98% of the stream and useless to
  a report), leaving every Summary block, header and error. When `rip_log.text` stops mid-record
  and `ripper_stdout.text` keeps going, **the difference is exactly what was lost** — a
  comparison that was impossible before, which is why the loss went unnoticed. It also means one
  uploaded file now serves the cyanrip project too: real-hardware stdout is the artifact they
  cannot produce for themselves.


### Fixed
- **A cancelled rip could silently drop a track that had completed and verified.** On the rig
  (2026-08-01) cyanrip's logfile was left at exactly **4096 bytes** — one unflushed stdio block,
  ending mid-token at `REPLAYGAIN_TRACK_GA`. Track 3 (*Message in a Bottle*, EAC CRC32
  `59D352DD`, AccurateRip v2 at confidence **200**) had finished 36 seconds before the cancel and
  was absent from `tracks[]`, from the EAC-layout log, and from the verdict — which then blamed
  the cancel for 12 tracks "never ripped" when the true figure was 11. The data was never lost;
  it is in the captured stdout and in the report's own `debug.lines`. The report was built from
  the file.
  Platterpus now **detects** the truncation and says so: `RipLog.log_truncated` /
  `last_track_incomplete`, a `log_parse.note`, an **error**-severity `ripper_log_truncated` issue,
  and an EAC-log banner that reads *"this is a FLOOR, not a count"* instead of asserting that
  tracks were never extracted. An intact partial rip still names its missing tracks — the fix
  removes an unsupported claim, it does not make the log vaguer.
  **Recovery is not in this change.** Rebuilding the report from the captured stdout is the
  larger follow-up; the parser cannot read stdout at all today (it opens a track on
  `Track N ripped and encoded successfully!`, which stdout never prints).

## [0.6.0] — 2026-08-01

### Added
- **The JSON report is now genuinely the only file worth uploading** (schema **v12**). Every
  hardware diagnosis so far has started by asking for a second file, so `.platterpus.json` gains
  an `artifacts` block carrying the **verbatim text** of the three companions written beside it —
  cyanrip's own `.log`, the EAC-layout render, and the `.cue` — each with its byte count and a
  SHA-256 of the bytes on disk. Text only, enforced by an extension allowlist: an audio path is
  refused and the refusal recorded (critical rule #8). A file that is absent says so rather than
  being omitted, and a **zero-byte** file reads as present-and-empty — the 0-byte `.cue` a
  cancelled rip left on the rig is invisible in a summary and obvious in a byte count.
- **`completeness` block** — `tracks_expected` / `tracks_in_report` / `complete`. The disc's track
  count already reached the report builder, but only to *feed* the verdict; it was never written
  down, so the JSON's only track count was `len(tracks)` — the log's own list, which a cancel
  shrinks. A reader had to parse English out of `verdict.message` to learn that a 2-track report
  described a 14-track disc. `complete` is tri-state: `null` means the writer didn't know, which
  is explicitly not a claim that the rip was whole.

### Fixed
- **"Open externally…", "Open rip folder" and Help → Open logs folder could silently do nothing.**
  `QDesktopServices.openUrl` returns False when nothing on the system claims the URL — no file
  manager wired up, or (the common one on a fresh KDE) no application associated with a bare
  `.log`. Three of the four call sites threw that bool away, so the click produced no window, no
  error and no log line: "may or may not work", decided by whether the machine happens to have an
  association. The window's own logs-folder button had always handled it *inline*, which is why
  the other three never got it. That fallback is now `ui/external_open.py`, shared by all four:
  a refusal shows the full path to copy and is written to the log file.
- **"View log" could show an errno instead of the log that was right there.** It preferred the
  backend's `.log` unconditionally, including when that file never appeared — while the real-time
  app log sat readable beside it. The choice is now made at *click* time, which is the one moment
  the answer is knowable; the backend log still wins whenever it exists.
- **The EAC-layout log said "INCOMPLETE RIP … 2 of 14 disc tracks" at the top and "All tracks
  accurately ripped" sixty lines below it** — two contradictory claims inside one SHA-256-attested
  document (real artifact off the rig, 2026-08-01). The end-of-rip status report decided its
  "clean sweep" sentence by comparing the AccurateRip total against the **log's own** track list,
  which a cancel shrinks; a cancel cannot shrink the disc. It is now handed the same
  `expected_track_total` every other surface uses — the number the rip was *asked* for — so a
  deliberate 2-of-14 selection still earns its "All tracks accurately ripped" while a cancelled
  one cannot.
- **A rip still in progress serialised "✓ Bit-perfect: all N tracks verified".** Found on the
  rig mid-rip: with 2 of 14 tracks done and the drive still spinning, `.platterpus.json` carried
  `"✓ Bit-perfect: all 2 tracks verified against AccurateRip (confidence 129+)"` and a green
  `level: "ok"`. The verdict guard added in v0.5.19 was being passed the right arguments — but
  its denominator, `_last_expected_track_total`, is snapshotted at **finish**, so every re-write
  *during* the rip handed it `None` and the "all N tracks" wording had nothing to contradict it.
  The EAC-layout log written beside it used the live disc count and said "2 of 14", so the two
  archival artifacts disagreed about the same rip — and if the app dies or the rip is cancelled
  at that moment, the JSON is the record left on disk. The in-progress writes now fall back to
  the same `expected_track_total` computation the finish path uses, which also folds in the Rip?
  selection so a *deliberate* subset is not reported as missing tracks.


### Documentation
- `docs/hardware-test-checklist.md` rewritten for v0.6.0: **A26** (the "open" buttons the
  maintainer reported, with a `grep` that says whether their machine ever hit the silent
  failure), **A27** (the 0-byte `.cue` a cancelled rip left — an open question with a
  control test that discriminates it), **A28** (the contradicting status report), and an
  **A24** rebuilt around schema v12 with every path quoted, since unquoted paths through a
  folder with spaces broke the last attempt. The *Send back* section now asks for **one
  file** — the report carries the rest.
- `docs/hardware-test-checklist.md` gains **A25**, which says plainly that v0.5.21's pre-gap fix
  has **no hardware proof and the usual test disc cannot give it one**: cyanrip reads pre-gaps
  from the TOC, and that disc's TOC declares none (EAC finds its ten by sub-channel scanning —
  the KDD-32 gap). A25 is a *screen*, not a rip: one `grep` over the app log after a disc scan
  says whether a disc can exercise the fix at all, with the likeliest candidates ranked. "None of
  my discs declare one" is recorded as a real result, so the fix ends up marked
  hardware-unprovable rather than silently untested.


## [0.5.21] — 2026-07-31

### Fixed
- **The fork's `Gaps:` block: all but the first line was discarded, and EAC's Gap handling row
  silently flipped to the *stronger* claim.** Stock cyanrip prints one summary line
  (`None signalled`); the fork enumerates one per track (`0 frame pregap in track 1, unmerged`).
  A one-line lookahead kept only the first, and — worse — the row's sense test looked for the
  literal word `none`, which that wording does not contain, so it fell through to
  `Appended to previous track` for a disc where cyanrip had reported **zero frames** and
  `unmerged`. That is the same category error that cost v0.5.18, reintroduced by a *ripper wording
  change* rather than by a code change. The block is now collected in full, and the row is decided
  from the measured frame counts plus the mode: all-zero frames render identically to
  `None signalled`, a merged mode earns `Appended to previous track`, and an unrecognised mode is
  left **unreported** with a logged warning rather than assigned whichever EAC phrase is closer.
- **A peak the ripper never measured could be rendered as digital silence.** The sample-peak
  sub-header path ran through an unbounded pattern, and `float()` has no 4300-digit ceiling — it
  returns `-inf`, which slipped past the "greater than zero" refusal and computed a concrete peak
  of exactly `0.0`. Bounded, and `_sample_peak_fraction` now refuses non-finite input so the
  guarantee does not depend on which pattern feeds it.

### Documentation
- **Four stale claims about upstream cyanrip corrected**, all surfaced by the fork session's own
  source reading. (1) `README.md` credited **PR #115** to cyanreg and presented it as the
  `INDEX 00` fix; it is **UltraFuzzy's, still open**, and it is the *exact pre-gap detection* layer
  — `INDEX 00` / `PREGAP` **cue reporting** was already merged upstream via **#104 / #118 / #122**,
  which no file in this repo named. (2) §2.4's premise that the `-Z` verdict is stdout-only and
  absent from cyanrip's log file was false at 0.9.3 and at master — **and that false premise is the
  root cause of the verdict-attribution bug above**, because it is what made indentation look like
  a usable signal. (3) The `-a`/`-t` colon bug is stated as "confirmed in master"; master **fixed
  it** (the function moved to `src/naming.c` and minds escapes), so the prepared upstream issue/PR
  is superseded — while Platterpus's own colon pass must **stay**, since we substitute U+2236
  *before* invoking cyanrip and removing the restore would ship U+2236 into every user's tags.
  (4) §2.1 ranked the sample peak as our best first upstream contribution with no mention of
  **#116** (UltraFuzzy) and **#148** (nicosp, 2026-07-24) already targeting it — and our proposed
  `ebur128` edit is specifically the half cyanreg pushed back on, in favour of a direct PCM scan.

### Added
- **The fork's own `Peak level: NN.N%` row is now read, and it wins over the dBFS sub-header.**
  Converting FFmpeg's 1-decimal dBFS print fabricates *exactly* `100.0 %` for any track peaking
  99.43–100 %, which in EAC's row means clipped — a claim about the audio the ripper never made.
  The fork's row is already EAC's unit and precision, is pre-rounding, and is gated behind
  `computed_crcs` so it cannot appear when no audio was decoded. When both are present and
  disagree, the percentage is kept and the disagreement is logged.
- **Which cyanrip *binary* produced a rip is recorded** (`ripper_build`, from the version banner's
  parenthetical — `release`, `fork`, a `git describe`). It is the only provenance separating a rip
  by an unreviewed local build from one by official 0.9.3.1, and two such logs of the same disc can
  carry materially different pre-gap metadata and peak values while both claiming `cyanrip 0.9.3.1`.
  Kept out of `log_creator` deliberately, so both committed reference logs are byte-identical.
- **`c2_pointers`, `paranoia_level` and `overread_mode` now reach the JSON report** (schema v11).
  All three were read from the log and rendered into the EAC-layout artifact but absent from the
  machine record, so an automated consumer could not see what the rip did. `c2_pointers` is the
  field the fork's §2.5 change exists to fill.
- A sub-minute `Extraction time` renders fractional seconds instead of `0:00:00`. The fork's
  measured `0.08 s` truncated to zero, which reads as "no time at all" beside an
  `Extraction speed 50.3 X` on the same track.

### Fixed
- **A track nobody looked up was reported as "in the database, and your rip disagreed with it".**
  Both the results table and the archival log asserted a comparison that never happened, and this
  is live on the cyanrip everyone is running — not fork-only. The evidence for "we compared" was
  the presence of a local checksum, on the written reasoning that cyanrip only prints a per-track
  `Accurip v1/v2:` row when the disc was found. **cyanrip prints those rows in every state**,
  `disabled` included, so the predicate was effectively unconditional: it made the "not in the
  database" state *structurally unreachable* for any cyanrip log, and every non-match — including
  one from a lookup that never ran — became `in DB, no match` / `Cannot be verified as accurate`.
  Platterpus now reads cyanrip's per-track `Accurip:` status row, which is the only line that
  states this directly, and a new `not-checked` state says plainly that no lookup was made. The
  local-CRC fallback is kept for logs with no status row (whipper's, where a local CRC really does
  evidence a comparison), so no existing rip is reclassified.
- **An all-zero AccurateRip checksum was rendered as a confidence-200 match.** cyanrip prints the
  caveat itself — `Accurip 450: 00000000 (match found, confidence 200, but a checksum of 0 is
  meaningless)` — and the confidence alone was enough to make it a positive offset-variant match,
  so a track nothing was meaningfully compared for announced a partially-accurate match on screen
  *and* in the attested log. It also inflated the partial tally and, with `rerip_offset_variant`
  off by default, excluded the track from being re-ripped. Guarded on the zero CRC rather than on
  cyanrip's wording, so a backend that omits the caveat is covered too. An **empty** CRC is
  deliberately not treated as zero: it means "not reported", and a whipper log can carry a real
  match without one — conflating them would have silently discarded genuine verifications, which
  is the same bug pointing the other way.
- **The AccurateRip state table could not notice a new state.** `test_surface_consistency`'s floor
  hardcoded four state names, so it was a floor equal to its own list — the third instance of that
  shape in two days. It now derives from `verdict.AR_STATES`, and adding `not-checked` failed it
  immediately until both surfaces and the case table covered it. The one state deliberately
  excluded now carries its justification in the map rather than being absent silently.
- **Every secure-re-read verdict was attributed to the wrong track on the maintainer's cyanrip
  fork — producing a false "verified" and a false "not reproducible" in the same attested log.**
  cyanrip emits its `Done; (N out of M matches)` verdict from inside the repeat loop, which runs
  *before* the `Track N ripped…` opener, so the line describes the track about to open. v0.5.19
  told the fork to **indent** that line and defined "indented ⇒ belongs to the track already
  open". The fork indented the string *in place*, still pre-opener — so indentation and position
  disagreed and every verdict shifted by one track. Measured on their real output: track 1
  converged (`Secure re-read: converged after 2 reads`) and Platterpus recorded `False`, then the
  EAC-layout log said `re-reads did NOT agree — this read is not confirmed reproducible` for it
  while giving the *non*-converged track EAC's strongest claim, `Test and Copy CRC identical`.
  The discriminator is now **position, never indentation**: a `Done;` line is buffered for the
  next track at any indentation, the labelled in-block `Secure re-read:` row is the only in-block
  source and wins, and the in-block `Done;` arm is deleted — no cyanrip has ever emitted one, so
  it was reachable *only* as the misattribution.

  **The root cause was a false belief in our own docs**, which is why they move in the same
  change: §2.4 recorded the `-Z` verdict as stdout-only and absent from cyanrip's log file. It
  was never absent — `cyanrip_log()` writes the logfile before stdout — so the line was always
  there, merely un-indented, and the whole indentation scheme was built on a premise the fork
  disproved by reading the source.

  Hardened alongside, because the consequence is worse than a wrong row: the auto-fix
  re-rip **file swap** gates on this boolean, so a shifted verdict can copy a read that never
  reproduced over audio that was fine. The swap now refuses unless the re-rip's log describes
  exactly the tracks that were requested, so a future attribution bug degrades to "don't swap".
- `Done; (0 out of N matches)` no longer parses as convergence. No cyanrip is known to print it
  as a final verdict, but the wording is demonstrably in cyanrip's vocabulary — its own
  `Repeating ripping (0 out of 1 matches …)` progress line — and a bare digit quantifier read a
  total failure to reproduce as a clean verdict. Pinned as an invariant, not a fix for an
  observed bug.
- **The EAC-layout log over-claimed every pre-gap by up to 89x, and it is a live bug on the
  cyanrip everyone is running — not a fork-only one.** cyanrip's `Pregap LSN:` row prints the
  **absolute position** where `INDEX 00` begins; Platterpus stored that number in a field called
  `pregap_sectors` and every consumer rendered it as a **length**. The error therefore grows with
  the track's position on the disc. Measured on the committed reference pressing: track 2's
  `INDEX 00` sits at LSN 14327 against a `Start LSN` of 14487, so the true gap is 160 sectors —
  **2.13 s**, exactly what real EAC 1.8 reports for that track — and the archival log said
  **3 m 11 s**. The length is now derived as `start_sector - pregap_start_lsn`, which is precisely
  how cyanrip computes the duration it prints in its own `(duration: …)` suffix; the raw position
  is kept as a separate, honestly-named `pregap_start_lsn`. Deliberately *not* parsed from that
  suffix: its fractional field is CD frames in some cyanrip formatters and hundredths in others,
  and no committed log pins which — subtraction is exact, a guess is not.

  Why it survived three releases with three green tests over it: **all three pre-gap tests
  constructed `TrackResult(pregap_sectors=N)` with a value that was already a length**, so they
  verified the *formatter* (which was right, and is still verified 10/10 against the real EAC
  baseline) and skipped the parser seam the bug lived in entirely. The reference disc's TOC
  declares no pre-gaps, so nothing else could have caught it. The new test starts from **log
  text** and asserts EAC's own `0:00:02.13`.


### Documentation
- `docs/hardware-test-checklist.md` A22 said an AccurateRip cell has "at most three distinct
  readings". It has **five** (`OK (N)`, `offset-variant match (N)`, `in DB, no match`,
  `not in DB`, `—`) plus a verbatim fallback for a state we don't classify. The sheet now
  tabulates all of them, so an unfamiliar-but-correct cell can't be reported as a failure —
  which is the specific way a too-tight expectation wastes a hardware run.


## [0.5.20] — 2026-07-31

### Added
- **Platterpus now reads the cyanrip lines the maintainer's fork will emit — without requiring
  them.** AppImage users run the *deployed* cyanrip 0.9.3, which prints none of these, so the
  whole change is written to one rule: **absent means absent.** A field no ripper reported stays
  `None` and every surface renders exactly what it renders today; the parse of every committed
  real log is byte-identical except for the one line below that 0.9.3 *does* print. Four new
  rows are understood (specification: `docs/cyanrip-upstream.md`):
  - **A per-track sample peak** (§2.1) fills EAC's `Peak level` row, in both plausible print
    shapes (inline `Sample peak:  -0.5 dBFS`, or cyanrip's existing sub-header style). The unit
    is required, never assumed. **cyanrip's existing `True peak:` can never reach this field** —
    it is a different quantity that legitimately exceeds full scale (all fourteen reference
    tracks do, 100.8 %–109.7 %), and EAC's row is a percentage of full scale that cannot exceed
    100 %. Two independent guards enforce it: the peak's own label decides which quantity it is,
    and any value above full scale is refused and logged rather than printed.
  - **A per-track extraction speed and elapsed time** (§2.3). The speed multiple fills EAC's
    `Extraction speed` row; the elapsed gets a row of its own, rendered only when measured.
    Deliberately *not* converted into a speed — what cyanrip's interval covers is unknown, so a
    derived number would be a guess wearing EAC's label.
  - **The `-Z` secure-re-read verdict written into the log file** (§2.4), with all three states
    it has: converged, did **not** converge, and not attempted. The middle one is why this
    matters — cyanrip's health line says "No errors occurred" for a track that never read the
    same way twice, so a log re-read from disk could not tell it from a clean one. An indented
    verdict belongs to the open track; the existing column-0 stdout form still buffers for the
    next track, unchanged. An unrecognised wording is *no opinion*, so it can never erase a
    verdict already measured (the GUI's own auto-fix verdict still wins).
  - **`C2 errors: supported by drive, not used`** (§2.5) now maps to a truthful `No` for EAC's
    `Make use of C2 pointers`. A bare `supported by drive` still maps to *unknown*, because that
    line states a drive **capability** and EAC's row asks what the rip **did** — the distinction
    that keeps the row honest.
- **`Appended: N frames of silence` is no longer discarded** — cyanrip 0.9.3 has been printing
  it all along (track 14 of both committed reference rips) and the parser's own enumerable check
  flagged it as the best line we still threw away. It names the track whose **final frames are
  fabricated silence rather than disc audio** — the per-track consequence of overread being off —
  so it becomes a per-track field and a line in the EAC-layout log's status report, beside the
  read-stability caveat and above the integrity checksum that covers it. The per-track blocks
  stay byte-comparable with a real EAC log, which is why the line goes in the status area.

### Added
- **The JSON report now records five per-track facts the parser had been reading and the report
  dropped** (schema **v10**). The report is meant to be the one file that explains a rip, so a
  fact that reaches the human-readable EAC-layout `.log` and not the machine record is a hole in
  that promise. The important one is **`appended_silence_frames`**, and it is *not* fork
  preparation — deployed cyanrip 0.9.3 prints `Appended: N frames of silence` on the last track
  whenever overread is off, and **both committed reference rips contain it**. It says that track's
  final frames are *fabricated silence rather than disc audio*, which is the most
  archival-relevant per-track statement in the log. Also added: `start_sector`, `end_sector` and
  `pregap_sectors` (the absolute geometry EAC's "TOC of the extracted CD" is derived from — the
  JSON previously could not rebuild a table the `.log` already showed), and the fork-only
  `extraction_elapsed_seconds`, so the fork's output lands in the report the day it ships rather
  than being parsed into a field nothing writes down. Every key is always present and `null` when
  unreported, so a reader can tell "the ripper didn't say" from "this build doesn't record it".

- **`docs/cyanrip-upstream.md` described shipped work as future work** in four of its
  five sections. §2.1, §2.3, §2.4 and §2.5 each said the Platterpus reader still had to be
  written — it shipped in v0.5.19 — which is exactly backwards for a document whose purpose is to
  be handed to whoever works on the fork: they would have read it as "the GUI is not ready for
  this yet". Each now states the shipped reader, the **exact** line shapes it accepts (both peak
  styles, all six speed/elapsed labels, all three `-Z` verdict forms), and — more useful than any
  of that — the constraints under which Platterpus **refuses** a value rather than printing a
  wrong one: the peak's unit is mandatory, a peak above full scale is rejected, an affirmative C2
  line must not be printed at all, and the per-track speed row must be indented or it collides
  with cyanrip's existing disc-level `Speed:` row.
### Fixed
- **One corrupt line of cyanrip output could end a rip in progress.** v0.5.19 closed the
  4300-digit `int()` hole in eight parsers, where the consequence is a field degrading to
  "unknown". It missed `workers/rip_worker.py`, where the consequence is different in kind:
  `_progress_for` parses cyanrip's **live stdout** from inside the read loop, wrapped in a `try`
  whose handler terminates the child and emits a rip error. A single unparseable progress line
  would have killed the rip *and* the disc read, minutes in. Eight sites are now guarded and all
  eight patterns bounded (`\d{1,4}` rather than `\d+`). The percent is worse than the integers
  and needed its own guard: `float()` does **not** raise on a long digit run, it returns `inf`,
  which survives every check and then raises `OverflowError` inside `int()` on the *GUI thread*,
  in a queued slot — a crash dialog over a progress bar. Both ends are now closed, the parse
  side and the bar itself.
- **The reason the above was invisible: the new sweep's floor was its own roster length.**
  `test_never_raises_contract.py` shipped with `assert examined >= 14` against a hand-maintained
  14-module list, so it could not fail for a module nobody had added — which is exactly what a
  floor is supposed to prevent. It now asserts every listed module was examined *and* that the
  list has not shrunk, and `workers/rip_worker.py` is on it. It found all eight sites above
  immediately.
- **The trust banner was assembled in two places, so whichever ran last won.** The banner is one
  sentence built from the AccurateRip verdict *and* the post-rip downgrade reasons ("this FLAC
  master failed its decode check"). `set_rip_log` wrote the first, `downgrade_verdict` wrote
  both, and `set_rip_log` carried a comment promising it re-applied any downgrade already
  recorded — which nothing did. It was correct only by accident, because `set_rip_log` happens to
  run exactly once per pane reset today; the unknown-album self-heal is one `return` away from
  ripping twice in a cycle, and the dedup guard would then have made the loss permanent
  (re-reporting the same failure returns early as a duplicate). The outcome is the one thing this
  screen exists to prevent: a green "✓ Bit-perfect" over a master that will not decode. There is
  now one renderer that reads both inputs every time.
- **`tests/test_regex_bounded_time.py` was timing 3 of 98 patterns and reporting a full sweep.**
  Any pattern whose single `.search` came in under the 200 µs noise floor was skipped — which is
  nearly all of them, since a fast pattern costs ~1 µs. It now times a repeated batch, so every
  pattern gets a real per-search figure, and a skip is a failure rather than a shrug. Two floors
  make that stick: every collected pattern must be measured, and the detector must still separate
  a known-quadratic pattern from a linear one (a threshold that flags everything is as useless as
  one that flags nothing, and only the pair rules out both).

### Changed
- `parsers/cyanrip_log.py` now routes every integer conversion through the shared
  `platterpus.safe_int.int_or_none` guard instead of a private copy of it. This was the module
  the never-raises hole was found in, and the one module still not using the guard that finding
  produced; each call site now also names its field, so an unusable value is diagnosable from a
  bug report. With `workers/rip_worker.py` above, v0.5.19's claim that the conversion "now routes
  through one shared guard" is finally true of the whole package — it was true of the eight sites
  that release fixed and of nothing else.

## [0.5.19] — 2026-07-31

### Fixed
- **Six post-rip steps edited files a previous rip had left behind.** The verification steps were
  scoped to "the files THIS rip wrote" on 2026-07-30 (`rip_files.rip_master_files`); the six that
  *mutate or derive from* what they find were not, and each still walked the album folder with
  `rip_dir.rglob("*.flac")`: unknown-mode tagging, the KDD-22 colon-restore metaflac pass, the
  FLAC re-compress, the transcode, and **both** cover-art embed loops (archive fetch and "cover
  art from a file"). One ordinary sequence contaminates that folder — cancel a rip (partial files
  remain), fix a track title, re-rip and choose *Replace*: the corrected titles produce new
  filenames, so the new files land *beside* the old ones. This disc's metadata was then written
  into the leftovers, they were re-compressed, they were transcoded into the user's library as
  MP3/WavPack, this album's cover was embedded in them, and the inflated count was reported back
  as "embedded in N track(s)". All six now go through the same shared helper, fed the finish
  handler's already-parsed `RipLog` through a new `rip_log=` seam so the log is read once and
  every step agrees on the same file list. Reads still degrade to a folder scan (logged at
  WARNING) when there is no usable log, so an older rip still gets art and tags.
- **A tagging failure was invisible: every FLAC could ship untagged under a window saying
  "Done."** `apply_track_tags` logs each per-file `MetaflacError` at WARNING and returns the
  files that succeeded — and the caller discarded that return value, so nothing else in the
  program ever learned about it: no signal, no status line, no report field. The scenario is
  ordinary (the disk fills during the metaflac pass; `metaflac` goes missing mid-album), and its
  outcome was a complete album with no metadata at all, reported as success. The pass now returns
  a structured result which reaches the GUI thread on a new `tagging_done` signal: the failing
  count and filenames go to the status line and the rip log view, the trust banner stops claiming
  ✓ (the audio *is* still bit-perfect — the banner text says so, and says the tags are missing),
  and the JSON report carries a `tagging_failed` entry in its existing `issues` list. A whole-pass
  crash is reported the same way instead of vanishing into `log.txt`.
- **A post-rip check that crashed was indistinguishable from one that passed.** `compute()` inside
  `_launch_post_rip_daemon` was unguarded, so an exception killed the daemon thread having emitted
  no signal and recorded nothing — and `_post_rip_work_settled` reads a *dead* thread as settled,
  so the library move filed the album away exactly as if every check had succeeded. The crash is
  now caught, attributed to its step, logged, and recorded on the window; the settlement gate in
  front of the library move reads that record and tells the user which check did not finish before
  it moves anything. The move still proceeds — the audio is unaffected and stranding it in the
  workspace would be worse — it just is not silent. (`threading.excepthook`, added in v0.5.18,
  logged the exception; a log line no code reads cannot change a decision.)
- **An invalid value in a hand-edited `config.toml` was reset to its default with only a log
  line — the silent reset the project's own *validate every input* rule forbids.** Resetting is
  right (an out-of-range value must never reach the ripper), but nothing on screen said it had
  happened, and one instance is actively dangerous: a `read_offset` outside its bounds becomes
  **0** while `override_read_offset` stays *on*, so the next disc is ripped at the wrong offset
  and nothing but the log file knows. The hazard was already written down —
  `main_window_drive._set_read_offset_override`'s docstring names "silently reset to 0 by the
  next startup's `_sanitized()` … ripping at the wrong offset with only a log line" — but the
  fix had been applied to the *write* path only, so a hand-edited file still walked into it.
  Every reset is now recorded with the field, the rejected value and the substituted default,
  and shown: a dialog once the window is up, and printed by `--doctor` (the no-GUI front end,
  where a log-only reset is the same silence). The same channel also covers an **unreadable**
  config — the loudest case of all, since every setting reverts at once — and says where the
  `.bad` backup went. The message text is built by a pure function
  (`settings_validation.describe_resets`), so it is asserted in tests rather than scraped out
  of a widget.
- **An album title of `..` wrote the rip outside the output directory.** cyanrip substitutes the
  album artist / album title / track title / track artist into the `-D`/`-F` naming schemes, so
  each becomes one folder or file name. It sanitises the characters that are *illegal* in a Linux
  path segment (`/` → `∕`, `:` → `∶`) but nothing maps `.` and `..`, the two segments POSIX
  reserves for *this* and *the parent* directory — so a value of `..` resolved a level above the
  chosen folder. This is the same escape fixed for `%Y` on 2026-07-28, closed then only for the
  one token Platterpus substitutes itself; the guard for it existed in
  `main_window_helpers.safe_path_segment` and was wired to the *unknown-album* path alone, while
  the ordinary known-disc path reached cyanrip verbatim. One pure check
  (`settings_validation.path_segment_issue`) now covers both roles: the track table refuses the
  value with a specific message before Start, and the argv builder refuses to build the rip at
  all, so nothing can hand cyanrip a directory reference. Deliberately narrow — `...`,
  `..and Justice for All` and a trailing dot are ordinary Linux names and still rip (Critical
  rule #3: cyanrip owns naming). Control characters are rejected on the same boundary, where a
  NUL previously reached `subprocess` and raised mid-rip.
- **`--ctdb-calibrate <folder>` validated nothing.** `argparse`'s `type=Path` constructs a path;
  it checks neither existence nor shape. A missing folder was reported as *"No .flac files found
  in …"* — the wrong subsystem, preceded by an unrelated warning about a missing rip log — and a
  *relative* folder named `-x` (`./-x` normalises to `-x`) made the FLACs under it come out as
  `-x/track.flac` argv entries, which `flac` and `metaflac` parse as **options**: an argument
  injection into a dependency, i.e. the output-validation half of the same rule. The folder is
  now validated and resolved at the boundary, with a specific error, a non-zero exit and a log
  line; an absolute path cannot be mistaken for an option. (`--compare` and
  `--assemble-best-of` already reported a bad report file specifically, and are unchanged.)
- **Eight "never raises" parsers that did.** CPython refuses to convert a decimal string of
  more than 4300 digits, so every bare `int(match.group(…))` fed by an unbounded `\d+` is a
  live `ValueError` — the character class proves the *characters* are digits and says nothing
  about the *length*. This was found and fixed once, in the cyanrip-log parser, and the fix
  plus its pinned test were scoped to that one module; **six identical holes in five other
  modules survived it** and each carried a docstring promising it could not happen. Corrupt
  external text would have taken down whatever called them: the drive list at startup, the
  disc scan, or the post-rip finish handler that writes the report. Now guarded in the EAC-log
  and whipper-log parsers (track number, AccurateRip version), the `cyanrip -I` and `cd-info`
  track counts, the drive-list read offset, the `whipper.conf` offset scanner, and all three
  MSF fields of the CTDB `.cue` reader — each degrading to "unknown" and logging *which* field
  was unusable, rather than raising. The conversion now routes through one shared
  `platterpus.safe_int.int_or_none` instead of being re-derived per call site.
- **A dead roster in the Settings dialog that read as the authoritative one.** A private
  `_goal_driven_widgets()` accessor, commented "the controls a goal preset drives", was called
  from nowhere *and* already wrong — it named five of the six, omitting the FLAC-verify
  checkbox, which is the very omission the code beside it records as a shipped bug. Removed
  rather than repaired: a second list is the drift.
- **A quadratic regex on user-edited text, parsed on the GUI thread before the window is
  shown.** The drive-offset CSV row pattern was super-linear in the line length — measured
  at **3.9 seconds** on a single 2000-character row — and that file is the documented way to
  install the full official AccurateRip drive-offset export, loaded by `MainWindow.__init__`
  *before the window appears*. One pathological row was a frozen startup with nothing on
  screen to look at: the never-block-the-GUI-thread rule broken by a regex rather than by a
  subprocess. Replaced with `rpartition(",")` — linear, fewer moving parts, and it splits on
  the *last* comma so a drive name containing one still parses.
- **Three more super-linear patterns bounded**, all fed external text of a length that is
  not ours to trust: the disc track count (unbounded `\d+`, 141 ms on a 4000-digit run), the
  generic version matcher (77 ms — it parses a dependency tool's `--version` output), and
  cyanrip's ETA string (67 ms). A CD holds at most 99 tracks and no version component needs
  ten digits, so the bounds lose nothing real.

### Added
- **The no-shell security guard can no longer pass by examining nothing, and covers two more
  holes.** Its three source scans asserted "no offenders" with no floor, so a renamed package
  or a broken glob would have turned the whole guard green while reading zero files (the
  project's own *can this check be satisfied by finding nothing?* question, unasked here).
  Both scans now have a floor and name what they expected to find. Two gaps closed alongside:
  `os.exec*`/`os.spawn*` are now banned with `os.system`/`os.popen` (`os.execl("/bin/sh",
  "sh", "-c", cmd)` is the same shell with a different name), and every `subprocess` call must
  pass an argv **list** — a single string first argument is legal for `subprocess.run` and
  slips past a `shell=True` check entirely, so an f-string, a `%`-format or a `" ".join(...)`
  in the command slot is now a failing test rather than a review item. All 18 existing call
  sites already comply; the guard is a ratchet, not a fix.
- **A cyanrip log line we don't understand is now a failing test instead of a silent
  omission.** Every bug this parser has ever shipped was the same shape — cyanrip prints a
  line and we quietly ignore it (the overread mode *twice*, the gap section, the
  `Accurip 450` offset variant, the per-track rip count) — and an if/elif chain cannot show
  that, because "we don't handle this line" and "there is no such line" look identical in the
  source. The disc-level rows are now ordered **tables** of (pattern → handler) entries, so
  the recognised set is data: a new test walks the committed real logs
  (`output_reference/cyanrip_*/`) and fails when a **column-0** line matches neither a table,
  nor a section header, nor an explicit `_IGNORED_DISC_LINES` allow-list entry *with a written
  reason*. 116 top-level lines are checked today, with per-log and total floors so a truncated
  or mis-globbed corpus cannot pass by examining nothing. The parser also logs (debug,
  bounded) any top-level line it did not claim, so a user's log file carries the evidence when
  upstream changes its output. Indented per-track detail is *reported* rather than failed — a
  tag dump is not a contract — but that report asserts every row carrying a trust claim (EAC
  CRC32, both Accurip lines, the LSN geometry, pre-emphasis, ReplayGain, paranoia counts,
  loudness) is still read. Each new check was verified by breaking what it guards: seven
  mutations (a dropped rule, a dropped allow-list entry, an over-broad one, a speculative one,
  an unlisted pattern, a lost per-track row, an empty corpus) all fail as they should.
- **`tests/test_never_raises_contract.py` — the never-raises rule, swept instead of trusted.**
  Two tests doing different jobs: a pinned-boundary behavioural table (one case per numeric
  field, so a failure names the field) and a *structural* AST sweep that fails when any new
  bare `int()` appears in a parser, including in a field nobody enumerated. The sweep earned
  its keep immediately — it found the drive-list offset site that the behavioural case had
  *missed*, because that payload's drive header didn't match the parser's regex and so never
  reached the conversion at all. Both carry floors (modules examined, conversion sites seen,
  and a check that the payload still trips CPython's limit) so neither can pass by finding
  nothing.
- **A completeness check on the Settings goal-preset wiring.** `test_goal_presets` now asserts
  the dialog connects one control per `GoalPreset` field, which is the invariant that both
  historical drifts violated. Verified by restoring the original omission: it fails with
  "GoalPreset sets 6 fields … but _wire_goal_presets wires 5 controls".
- **A sweep that catches the next one.** `tests/test_regex_bounded_time.py` times every
  compiled pattern in `src/` at two input sizes and objects only to super-linear *growth*,
  so a uniformly slow machine still passes and a flagged pattern is re-measured before it
  fails. It found all four offenders above on its first run — and it is what makes this a
  durable fix rather than four one-off ones, since the four had nothing in common except the
  shapes that backtrack, and nobody had noticed any of them.

### Changed
- **Characterization tests for the rip mixin's cancel / force-stop / finish paths** — the
  project's #1 bug-cluster file and, by a wide margin, its least-tested. `main_window_rip.py`
  under `tests/test_ui_main_window.py` goes from **81% (149 statements / 44 branch partials
  uncovered) to 96% (26 / 21)**, pinning the cancel → force-stop escalation, the synchronous
  shutdown drive-free, the KDD-30 auto-fix merge rules (including that a swapped-in re-rip never
  inherits the discarded read's AccurateRip verdict), the KDD-31 offset confirmation, the
  library-move settlement gate, and every post-rip step's crash / staleness / destroyed-window
  guard. Characterization, not aspiration: where a path looked wrong it was reported rather than
  pinned.
- **`parse_cyanrip_log` restructured without changing a single parsed value.** It was the
  highest-branch function in the codebase (57 branches / 415 lines, `ruff` PLR0912) and the
  densest source of shipped bugs of any parser; it is now 41 branches / 309 lines, with the
  plain "Label: value" rows moved into the tables above and the *section-scoped* parsing (the
  `Gaps:` two-liner, paranoia counts, album loudness, the per-track block and its `File(s):`
  lookahead) deliberately left as control flow — those blocks change what the FOLLOWING lines
  mean, and a table would hide that. The tables dispatch at exactly the four points the old
  if-chain tested those rows, because the section flags are cleared by "a line reached this
  block": merging them for tidiness would change parse results on odd logs. Proven neutral
  rather than asserted — every committed real log (cyanrip, EAC and whipper) plus synthetic
  logs for the shapes the real ones lack were dumped to JSON before and after, in two package
  trees differing only in this file, and the two dumps are byte-identical.
- **The in-progress track block is a typed dataclass instead of a bare `dict`.** A typo in a
  key ("copy_crc2") was a silent no-op no type check could see — on the fields that carry the
  bit-perfection claim. That was this module's single `disallow_any_generics` violation, so its
  `mypy` opt-out is now **retired** (rule #10's "retire one opt-out per commit"), leaving nine.
- **The test suite is ~16% faster** (measured 40–43 s → 33.5–35.6 s, and that saving repeats
  on each of the four CI Python legs). Two causes, both measured rather than guessed: the
  slowest test in the suite spent 4.02 s — 10% of the whole run — waiting out the real 4 s
  worker-abandon timeout, which is now shortened for that one test with the branch under test
  unchanged; and the quadratic track-count pattern above was costing the property-based
  parser test ~2 s per run.
- **The EAC log's `Pre-gap length` row would have disagreed with EAC on 9 of 10 values.**
  It rendered the fractional field as CD frames. Every *other* `FF` field in an EAC log is
  frames — the TOC table's are, and ours is byte-identical to EAC's there — but this one is
  **truncated hundredths of a second**, and the committed real EAC log proves it: one of its
  ten pre-gap values is `0:00:01.96`, and 96 is impossible for a 0–74 frame counter. Latent
  rather than broken today, because cyanrip 0.9.3 detects no pre-gaps on the reference disc
  so the row never renders — it goes live the moment cyanrip learns to (upstream PR #115),
  which is exactly when a silent unit mismatch is hardest to spot: the row would simply
  appear, look plausible, and be wrong. Pinned by three tests, including a sweep over every
  sub-minute sector count proving no rendering can emit an impossible `.100`.
- **Leftover files from an earlier rip were verified as if this rip had written them.** Cancel
  a rip (partial files, one truncated FLAC), fix a track title, re-rip and choose *Replace*:
  the corrected titles produce new filenames, so the new files land *beside* the old ones.
  Every post-rip check then globbed the album folder and reported on a mixture of two rips —
  CTDB built its disc TOC from 2N tracks and returned a spurious **"not in database"**, FLAC
  verify decoded the abandoned truncated file and produced a **⚠ FAILED** and a downgraded
  verdict for flawless audio, derived-verify's expected count doubled so a *complete* transcode
  read as incomplete, and the report's SHA256 manifest fingerprinted files this rip never wrote.
  "The files in the folder" was standing in for "the files this rip wrote", and those differ.
  The rip's own `.log` names one file per track, so that record — not the folder listing — now
  decides the list, via one shared `platterpus.rip_files` module all five call sites ask (the
  three verify workers, the checksum manifest, and the `--ctdb-calibrate` diagnostic), rather
  than five separate globs. Track order now comes from the log's numbering too, so an unpadded
  filename template can no longer put track 10 before track 2 in the CTDB TOC. Where no usable
  log exists (an older rip, a crash-truncated log, a folder named by hand on the CLI) it still
  falls back to the folder scan — verifying something beats verifying nothing — but the reduced
  confidence is logged with the reason, never silent, and any excluded leftover is logged by name
  so a verify covering 2 of 4 files is explainable from the log file.
- **The results table said a track was "not in DB" about a disc AccurateRip demonstrably
  has.** The durable EAC-compatible log learned four AccurateRip states — verified,
  offset-variant, *cannot be verified as accurate*, and genuinely absent — because calling a
  compared-but-unmatched track "not present in the database" is a false claim. The on-screen
  table was never told, and kept only four of its own five states, collapsing that case into
  **"not in DB"**: for a track cyanrip compared and missed (`not found, either a new pressing,
  or bad rip`) the log and the screen made contradictory claims about the same parsed track,
  and the screen made the false one. The cell now reads **"in DB, no match"** with a tooltip
  explaining that an unlisted pressing, a different drive offset and a genuine read error all
  look alike from there — so re-rip to tell them apart. The state is decided once per cell and
  the cell's text *and* tooltip both derive from it, replacing the third re-derivation at the
  call site.
- **The cross-surface consistency test was blind to the surface the bug was on.** Its docstring
  named four render surfaces while it imported three; the results table — one of the two it
  omitted — is exactly where the above defect lived. The table's per-track renderer is now on
  the roster, with an explicit four-state mapping and a case table covering every state, so the
  log and the screen must place a track in the same state or the suite goes red (the status
  line is called out in a TODO as the remaining gap).
- **A re-ripped track could report "AccurateRip verified" for bytes AccurateRip never
  saw.** When the auto-fix re-rips a bad track and swaps the better read into the album,
  every measured field is meant to come from the *shipped* read. The merge used a fallback:
  if the re-rip's log printed no AccurateRip line, the **first pass's** result was kept — and
  the first pass confirmed the bytes that were thrown away. Since that field is exactly what
  `track_accuraterip_verified` reads, the trust banner, the JSON report, the per-track table
  and the EAC log would all assert a verification that never happened for the audio on disk.
  The distinction now has a name in the code: a *description* may fall back to the first pass
  (losing a known fact is worse than a stale one), but a *claim of proof* may not — an
  unreported verification becomes **unknown**, and the drop is logged so a track does not
  silently lose its verdict. The Test CRC gets the same treatment, since pairing the first
  pass's with the replacement's Copy CRC renders a two-reads-agree convergence that never
  occurred. This was the worst finding of three audit passes and the exact class KDD-30 exists
  to prevent.
- **A deliberate partial rip was reported as a failure — a false alarm introduced by the fix
  above it.** Giving the trust verdict the disc's track count fixed the cancelled-rip case and
  immediately broke the intentional one: the Rip? column exists so a user can rip a subset, and
  a successful, deliberate 2-of-14 rip then read *"⚠ 2 of 14 tracks verified — 12 tracks were
  never ripped"* — the user's own choice rendered as a fault. The root cause was that "how many
  tracks should there be" had **three** defensible meanings (the disc's, the log's, the
  requested) and no name, so each of four fixes picked one and a different surface then
  disagreed. `verdict.expected_track_total` names it, and one number is now computed once and
  handed to every surface.
- **The same fix had reached three render surfaces out of four.** Six lines after the trust
  banner was given the disc count and the outcome, `fidelity_summary` — which feeds both the
  status line and the desktop notification — was still called with neither, so it kept
  computing the old wrong denominator. It now takes the same expected-track count. The audit
  that found this also found the project's own cross-surface consistency test was missing two
  of the four surfaces its docstring names.
- **The dependency report could claim a broken tool was installed — at a version read out of
  its own error message.** A version probe counted as successful the moment the command
  *finished*, whatever it finished with, and the version parser then took the first `N.N` it
  found anywhere in the output. Numbers in error text are plentiful and belong to other
  programs: a broken `cd-paranoia` saying `libcdio.so.19.0: cannot open shared object file`
  was reported as "cd-paranoia 19.0", and a dead `ripping` container quoting podman's own
  version was reported as that being cyanrip's — which also cleared the minimum-version
  floor, so nothing flagged it and the setup wizard that would fix it was never offered. A
  probe now counts only if the tool **exits 0** (every dependency's version flag was checked
  against upstream source and does exit 0; the rare non-zero-on-`--version` convention gets
  an explicit per-tool allow-list with its evidence recorded, never a blanket accept). A
  rejected probe logs the exit code and the tool's own captured output, so a bug report says
  *why* the tool was called absent. A probe cancelled mid-flight (SIGKILL → negative exit
  code) is likewise no longer readable as a version answer.
- **A rip you abandoned halfway became "your previous rip", and made a perfect re-rip look
  wrong.** Closing the window mid-rip leaves the worker's incremental snapshot in the album
  folder forever, stamped `outcome.status: "in_progress"` because nothing ever finalised it.
  The prior-rip scan filtered on the disc ID alone and never looked at that status, and the
  snapshot is re-written after every track so it carries the *newest* timestamp in the
  library — so it beat the user's real earlier rip, and the next clean rip of that disc was
  diffed against three tracks and warned "this rip has track(s) 4…14 the previous rip
  didn't" on a rip that was in fact flawless. Every report is now classified from its own
  outcome: an abandoned `in_progress` snapshot is never chosen as a baseline (and the skip
  is logged, so "why no comparison banner?" is answerable from the log file), while a
  **cancelled or failed** prior is genuine data and is still used — its tracks are real
  reads with real CRCs — but it loses to any complete rip of the same disc however old, and
  when it is used the headline says so in track counts instead of claiming a whole-disc
  match. A track the stopped-short side never reached is no longer reported as a change in
  either direction. Reports written before the `outcome` block existed still count as
  finished rips, so nothing in an older library is thrown away.
- **`--doctor` could report a PASS on the one check that matters most.** The backend-routing
  check — the only thing that proves the host → Distrobox → cyanrip chain is alive — treated
  *any* string `cyanrip -V` came back with as a pass, and printed that string as "the
  version". So a dead `ripping` container, a missing podman or an unexported binary passed
  the check with its own error message displayed where the version belongs, and a ripper that
  printed nothing passed with the literal "(no version output)" as its version — with
  `--doctor` exiting 0 on an environment that cannot rip. A pass now means cyanrip *answered
  with a version*: the probe must exit 0 (`version()` runs `-V` strictly, so a non-zero exit
  becomes an error carrying cyanrip's own words — this is visible only inside the adapter)
  **and** its output must contain a recognisable version, judged by the same version parser
  the dependency probe already uses. A failure quotes what the tool actually said and names
  which link of the chain is broken. A working cyanrip is unaffected, including a cold
  container whose startup chatter arrives *before* the banner.
- **The post-cancel drive rescue could force-kill and eject the WRONG drive.** Cancelling a
  rip arms a five-second rescue in case the in-container reader keeps spinning — and that
  rescue asked the drive picker for its *current* device when it **fired**, not when it was
  armed. So cancelling on `/dev/sr0` and then selecting `/dev/sr1` inside the countdown made
  it `fuser -k` and eject **sr1**: a drive it had no business touching, possibly one mid-rip
  in another window. The device is now captured when the rescue is armed, preferring the drive
  the rip is actually using over whatever the picker happens to show. The shutdown drive-free
  had the same flaw and the same fix. (Confirmed firing on the rig — the log shows the auto
  trigger running 5.1 s after a cancel.)
- **Closing the window during a rip could appear frozen for over a minute.** The shutdown path
  stops the in-container reader *synchronously on the GUI thread* — deliberately, because a
  daemon thread would be killed mid-`pkill` as the interpreter exits — but the kill sequence is
  up to seven subprocesses and each was capped at 20 s **independently**, so a wedged drive hit
  the sum. One shared budget now bounds the whole sequence (5 s, chosen against the 0.12 s the
  real fast path measured on the rig), and steps past the budget are skipped **and logged as
  skipped**, so a truncated shutdown is visible rather than looking like a sequence that ran
  and found nothing.
- **A logout, `kill <pid>` or Ctrl-C during a rip left the drive held.** `closeEvent` was the
  only thing that stopped the in-container reader, and podman does not forward signals into the
  container — so a session logout killed the GUI and left cyanrip ripping. Because the drive
  ignores its own eject button while a read holds the device, there was neither an in-app nor a
  hardware way out: the 2026-07-01 real-user bug through a third door. SIGTERM and SIGINT now
  close the window properly, going through the real `closeEvent` rather than a second copy of
  the teardown. Two subtleties are handled and documented: a pending Python signal handler does
  not run while Qt owns the event loop (a short relay timer gives the interpreter the chance),
  and a signal handler must not do real work between arbitrary bytecodes (it only records the
  signal; the timer slot does the shutdown).
- **"No cover art for this release" was also what an offline rip was told.** Every way the
  Cover Art Archive fetch could come back empty — a genuine 404, a timeout, a refused
  connection, an unidentified disc, an unusable reply — collapsed into the one line *"Cover
  art: none found for this release"*. "Nobody uploaded a cover for this disc" is final;
  "we could not reach the archive" says nothing at all about the release, and reporting the
  second as the first is the honesty rule inverted. Each reason now has its own sentence
  (an offline rip reads *"could not reach the Cover Art Archive — art was not fetched, so
  this release may still have one"*), a reason code we do not recognise names itself rather
  than inheriting "none found", and the reason plus the fetch's own error text now also
  reach the log file and the JSON report's `cover_art.error`.
- **A failed `metaflac` sample-count probe threw away the only explanation it had.** The CTDB
  verify path raised a bare `metaflac failed on 01.flac` and discarded metaflac's stderr, so
  a corrupt stream, a missing file and a permissions problem were indistinguishable — in the
  user-visible verdict *and* in the log. The exit code and the tool's stderr tail now travel
  in both, as does the `flac` decoder's stderr and any unparseable probe output.
- **A transcode that produced nothing left no log line at all.** When ffmpeg reported success
  but wrote no output file, the file was recorded as a failure silently, so a rip that
  derived no MP3s offered nothing to diagnose. Both branches now log — the exit code when
  ffmpeg says it failed, and the *absence* of output when it claims success — each naming
  the track, the target format and the fact the FLAC master is untouched.
- **A cancelled rip called itself "✓ Bit-perfect".** Cancel after two tracks of fourteen
  and the trust headline read *"✓ Bit-perfect: all 2 tracks verified against AccurateRip
  (confidence 129+)"* — green, over 14% of the disc — while the EAC log written beside it
  correctly said "covers 2 of 14 disc tracks". A 2026-07-28 fix had already made the verdict
  compare against a denominator, but the denominator was the number of tracks *in the log*.
  That catches a track which was ripped and failed (present, no CRC) and cannot catch one
  that was **never ripped**, because such a track is absent from the log and shrinks both
  sides of the comparison together. The verdict is now given the **disc's** own track count
  — the one number a stopped rip cannot move — and the rip's outcome, so the headline reads
  *"⚠ 2 of 14 tracks verified against AccurateRip — the rip was cancelled so 12 tracks were
  never ripped"*. The JSON report's `verdict` block gets the same two facts, so the file and
  the window can no longer disagree. Found on the rig, on a cancelled rip.
- **Pressing Cancel wrote nothing to the log, and neither did quitting.** The two most
  consequential things a user can do during a rip left no trace, so a report about a cancel
  that misbehaved — a drive left spinning, a rip recorded as failed — arrived with no record
  of when it was pressed, and a log could not even say whether the window had begun closing.
  Both now log one line: the cancel names the rescue-timer deadline, and the close names
  whether a rip was still live. Same diagnostic principle as the disc-probe fix in v0.5.18.
- **The EAC log's `Gap handling` row never actually spoke EAC's vocabulary.** v0.5.18
  claimed to fix this and the fix was unreachable: it only applied when cyanrip reported
  *nothing*, and cyanrip always prints its `Gaps:` block — so on real hardware the row
  still read `None signalled`, which is cyanrip's *detection result* sitting in a field
  where EAC states its *policy*. Two different facts, and the row consequently said nothing
  an EAC log says, which is the entire purpose of the file. It now renders EAC's own
  wording — `Not detected, thus appended to previous track` when cyanrip signals none,
  `Appended to previous track` when gaps were signalled, both verified verbatim against
  genuine EAC logs — and a log from any other ripper gets `(not reported by the ripper)`
  instead of leaking a parsed engine name into a policy row. Found on the rig, on the first
  run after the release that claimed it.
- **The test for that row could not fail.** Its fixture set `gap_detection` to EAC's phrase
  — a string cyanrip does not emit — so the renderer was handed its expected output as
  input and the assertion passed without the code ever producing it. The fixture now
  carries cyanrip's real text, and the row's wording is anchored to the committed real EAC
  log rather than to our own hand-authored one.

### Changed
- **`Make use of C2 pointers` is recorded as met where the hardware settles it.** cyanrip
  prints `C2 errors: unsupported by drive`, the parser already mapped that to `No`, and the
  rig's log confirms the row is filled — first-party evidence from the tool doing the read,
  which is the standard an earlier survey-based attempt was correctly refused for. A
  C2-*capable* drive still yields "(not reported)": cyanrip's line states what the drive
  can do, and EAC's row asks what the rip did.

### Documentation
- **A measurable archival gap against EAC is now documented instead of hidden.** Diffing
  the committed real EAC log against the cyanrip log of the same disc in the same drive
  shows EAC detecting pregaps on **10 of the 14** tracks where cyanrip's TOC read signals none.
  Both tools append the gap to the previous track, so the audio and the CRCs are
  unaffected — the *record* is less complete than EAC's. This is the same capability gap as
  KDD-32 / the `INDEX 00` work, which the finding now motivates concretely, and a test pins
  the disagreement so it cannot later be "fixed" by making our log print EAC's string
  regardless.
- **The hardware run sheet now carries *every* outstanding hardware test, not just the
  newest release's.** Three releases (v0.5.16–v0.5.18) landed between rig sessions, so a
  sheet scoped to one release left the older unproven items to be reconstructed from the
  session log by hand. `docs/hardware-test-checklist.md` is now grouped by *why a test is
  still open* — this release's new fixes (§A), shipped-but-never-proven from earlier
  releases (§B), never-exercised-on-hardware areas (§C), by-hand probes that answer an
  open design question (§D), and the ripper-swapping build test last (§E) — with test IDs
  stable across releases and retired once they pass, so the numbering gaps are the record
  of what the rig has already settled. Each of the ten new §A items names the release it
  came from and the failure it would expose, §A19 warns which log-wording changes are
  intentional so they don't read as regressions, and §A17 flags the one behaviour change
  this release that could plausibly regress a working setup.
- **The changes we want in cyanrip itself now have a ranked, evidence-graded home.**
  `docs/cyanrip-upstream.md` lists each gap in the external ripper with the
  real log lines that prove it, whether it affects the *audio* or only the *record*
  (every item is the record — none changes a ripped byte), the concrete upstream edit,
  and whether it belongs in an upstream PR, a soft-fork patch, or our own code. It
  complements rather than repeats the existing material: the roadmap owns the upstream
  *process*, the soft-fork doc the *runbook*, `scripts/cyanrip/` the *execution*. The
  census is derived by running the real EAC-layout exporter over the committed real
  cyanrip log — 44 labelled cells on the 14-track reference disc — so the list cannot
  drift from what the code actually cannot fill. Recommended first contribution: print
  the **sample peak**, because cyanrip's own track struct already carries
  `ebu_sample_peak` and already reads it, while its ebur128 filter is built
  `peak=true` and FFmpeg only computes `sample_peak` under `peak=sample` — so the field
  is dead and reads as full scale. Three items are closed rather than opened, including
  the confirmation that `-l` subset rips do **not** disable AccurateRip. Also records
  three corrections to our own record, the load-bearing one being that the reference EAC
  log lists `Pre-gap length` for **ten** tracks, not fourteen (the committed baseline
  file is two concatenated EAC logs, so a whole-file count doubles) — the finding stands,
  the number was wrong.

## [0.5.18] — 2026-07-29

### Changed
- **The rip report's JSON shape is now described in one place instead of implied by
  four modules.** `platterpus.report_types` names all 33 blocks as `TypedDict`s,
  derived from what the code actually writes rather than from a guess, so a
  contributor can see the wire format without reading the serialiser. Four of the
  fourteen modules on the strict-typing ratchet are retired by it (14 → 10). Purely
  descriptive: the emitted JSON is unchanged and 222 report/compare tests pass
  untouched.
- **Three `x or {}` fallbacks removed** where the empty dict was never a valid value
  of the thing it stood in for. Harmless while the type was a bare `dict`, a type
  error once the shape had a name, and a small lie about what the callee accepted
  either way.
- **`mypy --warn-unreachable` is documented as deliberately off, with the reasoning.**
  It reports five "unreachable" blocks and all five are false positives — one of them
  a cancel checkpoint that only looks dead because mypy reasons single-threaded while
  the flag is set from another thread. Deleting it would remove a real cancel in front
  of a ten-minute probe, so the trap is now written down next to the setting.

### Fixed
- **Deselecting a track wrote every tag onto the wrong file.** The unknown-disc
  tagger took each track's number from the file's *position* in the list rather than
  from the file itself. That is only the same thing when every track was ripped — and
  the Rip? column exists precisely so it isn't. Untick track 1 and the file `02 - …`
  was written track 1's title and `TRACKNUMBER=01`, `03 - …` got track 2's, and so on
  down the disc: **every tag on the archival master silently off by one**, with the UI
  reporting success and nothing in the log. Both tagging paths (edited and
  placeholder) took the number from the filename now, and a file whose name carries no
  number is skipped with a logged reason rather than guessed at — a wrong track number
  is indistinguishable from a right one to everything downstream, so it is worse than
  a missing one. The tests that should have caught this used filenames no rip ever
  produces (`a.flac`, `track1.flac`), which made position and track number agree by
  construction.
- **A rip that finished but whose log couldn't be found ran every post-rip step over
  the entire music library.** The album folder is derived from the log's location, and
  when there was no log the code fell back to the configured *output root*. Each step
  then walks that recursively — so tagging, colon-restore, FLAC recompression, MP3/WAV
  derivation and the checksum manifest all applied to every album previously ripped,
  and the report hashed the lot. Reachable in practice: the log is located by
  modification time, so a clock adjustment during a long rip loses it. Those steps are
  now skipped with a clear explanation, and the disc still ejects if that was
  requested.
- **A failed disc read was reported as "this disc isn't in MusicBrainz", with nothing
  in the log.** The disc probe threw away cyanrip's exit code *and* its error text, so
  a permission problem on the drive, a dead `ripping` container or a broken host
  export all produced an empty disc — which is indistinguishable from a real disc
  MusicBrainz has never seen. The app then offered an unknown-album rip while the
  actual cause (e.g. the user's account not being in the `cdrom` group) went
  unmentioned anywhere, so a bug report carried no evidence at all. A failed probe now
  reports the failure, quoting the tool's own words, and every non-zero exit is
  written to the log.
- **Exceptions on the background threads that do the post-rip work went nowhere.**
  Only `sys.excepthook` was installed, which does not cover plain threads — those go
  to `threading.excepthook`, whose default writes to a stderr an AppImage launched
  from the applications menu does not have. So a failure in hashing, verifying,
  transcoding or moving was invisible: not the log, not the report, not the screen.
  The user saw a step silently never finish.
- **The crash dialog could itself crash or hang the app.** An error escaping a
  background task raises on *that* thread, and the handler built a message box there
  — which Qt forbids for widgets, and which can block forever, stranding the thread.
  It now logs instead of drawing when it is not on the GUI thread. (A crash handler
  that is unsafe exactly when it is needed is worse than not having one.)
- **Closing the window during the startup dependency check or a disc scan waited it
  out instead of stopping it.** Both block inside a container call that cannot be
  interrupted by the usual means, and both had a working stop that **nothing called**
  — the teardown omitted one argument, which is all it takes for a cancel to become
  dead code. Closing is now prompt, and a test enforces that every worker's stop is
  actually invoked, not merely present.
- **Cancelling the "Set up drive" wizard or a disc scan now really stops the drive.**
  The machinery for killing a probe mid-flight is in one place instead of two, which
  also fixed a defect the duplication had hidden: superseding a disc scan (the
  "Rescan disc" button) left the previous reader running *and* made the new one
  unkillable, because both were tracked in the same slot and whichever finished last
  cleared it.


### Added
- **The thread-safety rules are now swept across the whole codebase instead of being
  enforced for one class.** Every rule that mattered this cycle existed in writing and
  was checked in exactly one place: `MainWindow`. Nine classes create worker threads;
  one was tested. The dialog that turned out to have no teardown at all was found by a
  person reading code, which is not a control. Four new sweeps derive their targets
  from the source tree, so a class added next month is covered the day it is written:
  - **every `QThread` owner must stop its threads from a teardown hook** — resolved
    through the MRO (so a mixin creating a thread that the concrete window stops is
    correctly attributed) and requiring the stop to be *reachable* from `closeEvent`
    or `reject`, not merely present somewhere in the class;
  - **a `cancel()` that only sets a flag must be justified in an allowlist**, turning
    "do not ship a flag-only cancel" from a written rule into a build failure with a
    forced written reason. Two entries qualify today and both say why;
  - **a ratchet on the five workers that expose no `cancel()` at all** — it may shrink,
    never grow, so the known gap cannot spread to a sixth worker.

  Verified the way the rest of this cycle was: reverting each fix makes the
  corresponding sweep fail and name the exact class and attribute.

### Fixed
- **`stop_thread` had nothing to cancel for five of the nine workers**, which is now
  recorded and bounded rather than unnoticed. `quit()` cannot reach a thread blocked in
  a subprocess or socket read, so closing the window waits out the shutdown budget and
  abandons those threads. That is safe — abandonment retains the reference and makes
  exit skip interpreter teardown — but it is not cancellation, and closing it properly
  needs the killable-child treatment the cache probe now has.

## [0.5.17] — 2026-07-29

### Fixed
- **Cancelling or force-stopping a rip could hang the app forever on a full pipe.**
  The rip worker ended with an unbounded `wait()` on the ripper, and the loop that
  drains the ripper's output does *not* always run to the end — on cancel it stops
  early. A pipe holds about 64 KiB; once it is full the ripper blocks trying to
  write to it, so it never exits, so the wait never returns. It was waiting on the
  rip worker's own thread, so that thread never finished either and got abandoned at
  shutdown. Python's own documentation warns about exactly this combination. The wait
  is now bounded and escalates to a SIGTERM-then-SIGKILL of the whole process group,
  which ends the writer and so actually breaks the deadlock rather than just timing
  out of it.
- **The escalation that was supposed to stop a ripper ignoring SIGTERM did not
  exist.** `RipHandle.cancel()` implemented it fully and was called from **nowhere**
  in the codebase, while the cancel path's own documentation pointed at it as the
  thing that would kill a stubborn rip. Now wired in. Its final wait is bounded too,
  because SIGKILL does not land on a process stuck in a drive ioctl — an unreapable
  ripper is reported and logged instead of blocking a thread for good.
- **Closing the drive-setup dialog left `cd-paranoia` reading the disc.** "Cancel"
  called a hook that is a deliberate no-op on the base class and which the cyanrip
  backend never overrode, so cancelling set a flag that the blocked call never reads
  — and the flag is only checked *between* the wizard's two steps, one of which can
  run for ten minutes. The disc kept spinning with the drive's physical eject button
  ignored, because a read holds the device. Three separate comments claimed this
  already killed the subprocess. It does now: the probe runs in its own process
  group and is killed on cancel, including when the cancel arrives during startup,
  and a probe that times out is killed instead of left running.
- **The pending-installs dialog had no teardown for its worker thread.** The dialog
  refuses to close mid-install, so no user action could reach a live thread — but
  that guards intent, not object lifetime: the thread is parented to the dialog and
  the dialog to the main window, so a close coming from *above* destroyed a running
  `QThread`, which Qt treats as fatal. It now goes through the shared stop path,
  which abandons the thread safely and counts it, so exit skips teardown instead of
  aborting. The install itself still cannot be interrupted — the work is an injected
  callable that owns its own subprocess — and that limitation is now written down
  rather than papered over with a cancel that would do nothing.
- **The "Set up drive" dialog clipped its own text when made smaller.** Its minimum
  size was a hand-picked 460×320, which is 185 px shorter than the content actually
  needs: measured at 440×300 the intro label was **73 px short**, so the explanation
  of what a read offset *is* was simply not drawn (and with a known offset shown,
  three labels were clipped). The minimum is now derived from the laid-out content,
  so the dialog refuses to be shrunk into clipping. A scroll area — the fix used for
  the results pane — would have been wrong here: the results box is already a scroll
  area, so it would have become *nested*, which is the bug v0.5.16 removed.
- **The test suite had been reporting a green build while running only 76% of
  itself.** `conftest` ends the session with `os._exit(status)` on purpose (it
  dodges a PySide global-teardown abort), which makes *any* mid-run `os._exit(0)`
  indistinguishable from success — same exit code, no summary line, no coverage
  report, `--cov-fail-under` never evaluated. Product code supplies exactly such a
  call: `platterpus.hard_exit` leaves the process without teardown, and a test that
  drives the update-relaunch path called it for real. So the run stopped partway,
  **~500 tests never executed**, and CI marked the job ✅ — which is what the
  previous release was merged on. Found by noticing a captured run had no summary
  line, then confirming the same truncation in the CI log.

  Three things now have to hold for a build to be green. The injection seam that
  existed for this (`hard_exit._exit_fn`, documented as the way to test the exit and
  never once used) is patched from an **autouse** fixture, so no test has to know
  the hazard exists; the stand-in **raises** instead of returning, because
  `os._exit` never returns and a stub that falls through lets tests run code
  production cannot reach; and the session now writes a completion sentinel as its
  last act which **CI verifies**, because a truncated run cannot report on itself.
  Reverting the fixture reproduces the original failure exactly: a failing test
  swallowed, exit status 0, sentinel absent.
- **A second update-relaunch test had never run at all** — it sat after the one
  that killed the session, so it was silently skipped every time. It passes now
  that the suite reaches it.
- **CI suppressed pytest's `N passed` summary** by passing `-q` on top of the `-q`
  already in `addopts` (verbosity `-2`). That line is the only human-visible proof
  in a log that a run reached the end, so its absence looked normal and hid the
  truncation above.

### Changed
- **The two tools that gate CI are now pinned to the minor they were measured
  against.** `ruff format` and `mypy --strict` change what they accept between
  minor releases, so the previous wide ranges (`ruff>=0.15,<1`,
  `mypy>=1.13,<3`) meant a routine upstream release could turn CI red with zero
  change to our code — reading as a code problem, not a dependency one — and let
  a local checkout and CI resolve different versions and disagree about a green
  build. Bumping either is now a deliberate commit that re-runs the gate.
  Non-gating tools (`pytest`, `hypothesis`, `pytest-cov`) stay loose.

### Fixed
- **Cancelling a rip and then quitting within five seconds left the drive
  reading, with no way to recover.** On Cancel the host-side wrapper dies at once
  but podman does not forward the signal into the container, so the only thing
  that kills the in-container reader is a five-second rescue timer — and
  `closeEvent` disarmed that timer *before* the shutdown drive-stop ran, while the
  shutdown stop itself gave up whenever the rip already looked finished. Quitting
  inside that window therefore left the reader ripping, and the drive's physical
  eject button is ignored while a read holds the device, so there was no in-app
  *or* hardware recovery. This was the 2026-07-01 real-user bug reachable through
  a different door. The shutdown stop now also fires when a force-stop is still
  pending, and the timer is disarmed only after it has been consulted.
- **Pressing Force stop was permanently recorded as a rip *failure*.** Only the
  Cancel button marked the rip cancelled, so using Force stop on its own (it is
  enabled for the whole rip) produced "Rip failed.", an `outcome.status` of
  `failed` in the JSON report, an `*** INCOMPLETE RIP (failed) ***` banner in the
  checksum-signed log, **and** a failure notification — recording the user's own
  deliberate choice as a malfunction. It is now recorded as a cancellation.

- **Closing the window during a rip aborted the process.** A threading audit found
  that `closeEvent` stopped six worker threads and not the rip thread — it
  cancelled the rip *worker* and freed the drive, but `_rip_thread` is parented to
  the window, so `~QMainWindow` destroyed a live `QThread`. The usual safety net
  does not apply here either: `worker.finished → thread.quit` is a **queued**
  connection to the GUI thread, so once `app.exec()` has returned that `quit()` is
  never delivered and even a cleanly-finished worker leaves its thread spinning.
  Reproduced to exit 134. The test suite could not have caught it — its own window
  fixture stops the rip thread, silently compensating for the gap — so the
  regression test asserts on `closeEvent` itself.
- **`--uninstall` could abort the same way.** That path returned from `main()`
  without the abandoned-thread check, and its worker shells out to podman/dnf with
  a cancel flag that is only polled *between* steps (a step's timeout is 1800 s),
  so closing mid-teardown reliably abandons a running thread.
- **The hard exit had started firing on every quit.** One call site abandons a
  thread unconditionally (a rescan superseding an in-flight disc probe waits 0 ms)
  and the retention list was append-only, so a single mid-probe rescan latched the
  count for the rest of the session — turning "skip teardown only when it is
  unsafe" into "never run teardown", and `atexit` never ran. Finished entries are
  now pruned, so only a genuinely-live thread forces the hard exit.

- **The app aborted with `SIGABRT` when it exited while a worker thread was still
  blocked in a container call** — reliably during the update-relaunch, which
  tears the process down with background work in flight. A worker inside
  `subprocess.communicate()` never returns to its event loop, so `QThread.quit()`
  cannot reach it; `stop_thread` gives up after a short wait and abandons the
  thread, keeping a reference so the garbage collector can't destroy a running
  `QThread`. That retention was already there when it crashed — and it is not
  enough, because it lives in a **module global, and CPython clears module
  globals during interpreter shutdown**. The last reference dropped at exit,
  `~QThread()` ran on a running thread, and Qt called `qFatal()`. Reproduced: a
  child process that abandons a running thread and then exits normally dies with
  **134 (SIGABRT)**, logging `QThread: Destroyed while thread 'DiscInfoWorker' is
  still running` — the exact line from the crash report. Both exit paths now
  bypass interpreter teardown when a thread was abandoned still-running: they
  flush the log explicitly (`os._exit` skips flushing, which would truncate the
  log a bug report depends on) and leave immediately. A clean shutdown is
  unchanged and still unwinds normally.
- The relaunch and normal-exit paths share one guard (`platterpus.hard_exit`), so
  they cannot drift apart the way they had.

### Changed
- **Worker shutdown now shares one 10-second budget instead of giving each worker
  its own timeout.** The old per-worker wait was 2000 ms, which could not cover a
  cold container exec (measured at 3.45 s), so workers that were about to finish
  got abandoned anyway. The obvious repair — raise the per-worker timeout — would
  have been worse here: `closeEvent` stops six workers, so a 10 s wait each is up
  to a **60 s frozen window** on close. `ShutdownDeadline` bounds the whole
  teardown at 10 s and hands each worker whatever is left; when the budget runs
  out the remaining workers are abandoned immediately, which is now safe. The
  single-attempt default rose 2000 ms → 4000 ms so a cold exec is covered when
  there is budget for it. All timeouts are named constants.

- Thread handling no longer says **"detaching"**. Qt has no detach operation —
  there is no API that severs Python ownership from C++ lifetime — and the word
  made a fatal pattern look like a supported one. It now says "abandoning", and
  the log line states the consequence: the reference is retained and process exit
  must bypass teardown. A test keeps the word out of the code and the log
  messages (while still allowing the comment that explains why it is banned).

## [0.5.16] — 2026-07-29

### Changed
- **The results pane is now three bands instead of one long column, so it never
  shows two scrollbars at once.** v0.5.15 stopped the pane painting text over
  itself by putting everything inside a scroll area — and the table and the live
  console are themselves scrollable, so inside it they became *nested* scroll
  surfaces: two vertical scrollbars 15 px apart (measured at x=911 and x=926 on a
  940×400 pane), with the wheel acting on whichever one the pointer happened to be
  over. The maintainer's report was exact: "difficult to use together".

  The obvious repair — turn the inner scrollbar off and size the table to its
  content — was measured and rejected: **a nested scroll area that has nothing
  left to scroll does not pass the wheel on to its parent**, so it trades a
  visible scrollbar for a *dead wheel zone* over the biggest widget in the pane,
  which feels more broken rather than less.

  So the pane no longer nests anything. A **fixed header** keeps the progress
  bars, the status line and the trust verdict permanently on screen; a
  **QTabWidget** holds *Tracks* (the per-track table), *Details* (the CTDB
  verdict, the AccurateRip reconciliation and album loudness) and *Live log*; and
  the four output buttons stay pinned at the bottom. Because only one tab is
  visible, there is at most one scrollbar and it can never be nested — measured
  at every size from 1900×980 down to 940×300, on every tab, with zero
  overlapping widgets, so the v0.5.15 fix is preserved rather than traded away.

  Two things keep the tabs from hiding anything. The pane **follows the rip**: the
  live console is shown while ripping and the per-track results come to the front
  when the log lands (unless there are no tracks, in which case the log stays —
  it is the only thing that can explain why). And the **Details tab label carries
  a ⚠** whenever a caveat is sitting behind it, so a warning can never wait
  silently for a click. Alt+T / Alt+D / Alt+L switch tabs.

## [0.5.15] — 2026-07-29

### Fixed
- **The results pane really does stop drawing its text on top of itself now.**
  v0.5.14 claimed this and did not deliver it: it fixed a genuine problem on the
  *horizontal* axis (an un-wrapped label made its whole line the pane's minimum
  width, so the window refused to narrow) but the reported symptom was on the
  *vertical* axis, and wrapping a label slightly increases vertical demand — so
  the release marginally worsened the thing it was credited with fixing. The real
  mechanism, reproduced with the real hardware rip log before anything was
  changed: a `QVBoxLayout` given less height than its children need does not clip
  and does not scroll — it **overflows, and the children's rectangles collide**.
  Compounding it, the pane under-reported what it needed (a word-wrapped label's
  minimum height is *one line* while the height it draws is two or three), so it
  claimed a 326 px minimum and then allocated ~405 px. Below that the verdict
  banner was painted across the live-log box and the CTDB line across the
  AccurateRip table's first row — exactly what the screenshot showed. The pane's
  contents now live in a scroll area, so "not enough room" becomes a scrollbar
  instead of a collision: measured at zero overlapping widgets from 620 px down
  to 200 px of height, where the old code overlapped below 326 px. The rejected
  alternative (teaching every label to report its true height) also removed the
  overlap but drove the pane's minimum height to 1418 px — a window taller than
  most screens.

### Changed
- **The desktop completion notification now records what it did.** Whether it
  fired was unanswerable from `log.txt`: the success path logged nothing and the
  failure path logged at `debug`, so the first hardware test of the v0.5.13 fix
  was inconclusive purely because the maintainer stepped away while the toast was
  on screen. Every outcome is now an `INFO` line — posted (with the text), or
  skipped and why (turned off in Settings, rip cancelled, or no usable system
  tray) — and a genuine failure is logged with its traceback rather than
  swallowed at debug level. A courtesy feature still has to be diagnosable.

## [0.5.14] — 2026-07-28

### Fixed
- **The results pane and disc panel drew their text over each other in a
  non-maximised window.** Two labels were never told to word-wrap, and an
  un-wrapped `QLabel`'s minimum width is the width of its entire single line —
  a minimum that propagates all the way up to the window. Measured: a real
  end-of-rip status line demanded **906 px** of minimum width against 366 px
  for the idle text, and the disc panel's value labels pushed its minimum from
  208 px to **575 px** once they held real post-rip values. Below those widths
  the layout physically could not comply, so the contents overflowed their
  viewport and the CTDB and loudness lines were painted on top of the
  AccurateRip table. Maximised it looked correct, which is why it survived this
  long. Both labels now wrap, so the panes shrink with the window; disc IDs are
  single tokens with no spaces, so they still reserve their own width and are
  never broken across lines. Found on real hardware, 2026-07-28.

## [0.5.13] — 2026-07-28

### Fixed
- **The desktop "rip complete" notification never fired.** v0.5.12 replaced a
  `getattr(self, "_tray_icon", None)` with a plain attribute read to satisfy the type
  checker, and declared the attribute on the window's typing seam — but that seam's
  declarations live under `if TYPE_CHECKING`, so they inform mypy and create nothing
  at runtime. The read came before the only assignment, so every completed rip raised
  `AttributeError` and the notification was silently swallowed as best-effort. Found
  in the log of a real 14-track rip. A type-only declaration is not an initialisation.
- **The test suite could segfault at any point, and had been able to for most of
  the project's life.** Measured: unmodified `main` died with SIGSEGV on 5 runs out
  of 5. `deleteLater()` never executes in a suite that runs no event loop, so Qt
  objects accumulated; post-rip work runs on daemon threads; and a cyclic garbage
  collection can begin on *any* thread, so whichever thread was inside the
  collector when the GUI thread destroyed a widget was the one that died — which is
  why the traceback always named an unrelated file. The cyclic collector is now
  paused for the duration of each test and runs at one deterministic point on the
  main thread after every worker has been joined; the window teardown covers all
  seven Qt worker threads and all nine daemon threads instead of four and none; and
  a new fitness test forces a full collection every run so this cannot silently
  return. No shipped code path is affected — this is test infrastructure — but it
  made CI unreliable and it was hiding behind whichever test happened to trigger a
  collection.


## [0.5.12] — 2026-07-28

### Fixed
*Found by a whole-application audit (typing, security, architecture, UX honesty,
documentation) run across eight parallel reviewers, 2026-07-28.*
- **External tools were resolved through `PATH` alone, so a desktop-launched GUI
  could not find its own container-exported binaries.** `flac`, `metaflac`, `ffmpeg`
  and `sox` now resolve via a shared `tool_paths.resolve_tool()` that falls back to
  `~/.local/bin` (where `distrobox-export` puts them) before giving up. A GUI started
  from a desktop icon does not inherit a login shell's `PATH`; the wizard would report
  the tool installed while the dependency probe reported it missing.
- **Switching the Settings goal preset did not move the "Verify FLAC after the rip"
  checkbox**, so the summary line described a setting the preset had not applied.
- **Six user-facing strings in `drive_access.py` still said "whipper"** — the backend
  was removed in v0.4.x (KDD-18). They now say cyanrip.
- **The EAC-layout log forged a `Test CRC == Copy CRC` pair for a track whose
  re-reads explicitly *disagreed*.** `rip_count` is how many passes cyanrip *took*,
  not how many *agreed*; a `-Z` run that hits its repeat limit prints both "no
  matches found" and "(after 5 rips)", and `or reads >= 2` short-circuited the
  measured negative. One SHA-256-attested document asserted the reads were
  identical *and*, in its own status report, that they were not.
- **The `*** INCOMPLETE RIP ***` banner has never rendered in the shipped app.**
  `_last_outcome` is a dict and the call site read it with `getattr`, so the status
  was always empty — the v0.5.9 "an interrupted rip declares itself" fix was live
  only in the renderer, never through the wiring. Its regression test now goes
  through `_write_eac_log`, which is where the seam actually is.
- **An interrupted securing pass reached the JSON report but not the durable log**,
  so of the two records for one rip the archival one was the more reassuring.
- **The green "Bit-perfect" banner dropped failed tracks from its denominator.** A
  track that produced nothing at all was invisible to the count, so the trust
  headline read "all N tracks verified" beside a status line saying one was missing.
- **"Matched an offset-variant pressing" was counted from the presence of an
  `Accurip 450:` line**, including "(not found)" — so the banner claimed a partial
  match while the table beside it showed "—". One shared predicate now decides it.
- **The verdict banner never heard about post-rip failures.** A FLAC master that
  fails `flac --test`, a lossless derived file that isn't bit-identical, or read
  instability that survived the auto-fix now downgrade the banner instead of leaving
  a green headline over a broken result.
- **`validate_config()` failed open**: one non-string field made the first rule raise
  and the single catch-all swallowed it, returning an empty issue list — which
  `Config._sanitized()` read as "valid" and used to persist a `..`-traversal
  template, an absolute template and an out-of-range offset. Each rule is now
  isolated, and the path/template/tool-path validators type-check before parsing.
- **`%Y` could escape the output directory.** It is the one naming token Platterpus
  substitutes rather than cyanrip, and it took the Year box's text verbatim, so a
  year of `../.` wrote the album outside the output folder — while the Settings
  preview, which does sanitise, showed the safe string.
- **The read offset reached `cyanrip -s` from three paths that never validated it**
  (wizard entry, auto-detect, and the user-editable `drive_offsets.csv`). It is now
  bounds-checked at the single write path, with a visible message on refusal, and
  the wizard's spin box reads the validator's bounds instead of its own.
- **Five reads of external files could raise `UnicodeDecodeError`** — a `ValueError`,
  so every `except OSError` guard missed it. One is `DriveProfileStore.load`, called
  from `MainWindow.__init__`: a corrupt cache locked the user out of the app.
- **Embed-only cover art destroyed an existing `cover.jpg`.** metaflac imports a
  picture from a file, and the scratch write reused the canonical library name and
  then deleted it — on the *default* setting.
- **A slow cover-art fetch could write album A's result into album B's report.** Two
  of the three post-rip emits lacked the generation guard the third had.
- **An unmounted volume silently rewrote your settings.** "This folder isn't writable
  right now" was graded an error, and `_sanitized()` resets error-level fields on
  load — so a NAS or removable rip library that wasn't mounted at launch was
  retargeted to `~/Music/rips` and the library folder cleared. It is now a warning.
- **`uninstall` orphaned `~/.local/bin/cd-paranoia`** — the exact repeat of the
  `flac` bug (#34) that the teardown docstring memorialises.
- **The overall progress bar froze at 95% on every successful rip.** The last 5% was
  reserved for a whipper-only phase cyanrip never emits.
- **The desktop notification sent a stale summary** — the one captured before the
  read-stability warning overwrote the on-screen line, so the unattended user was
  told "all tracks ripped cleanly" while the window said otherwise.
- **`issues: []` read as "clean" for a rip nothing could verify.** A CTDB no-match and
  a rip with no AccurateRip match at all now say so; `_issues` was accepting the CTDB
  block and never reading it.
- **A failing test run printed no failure names and no tracebacks.** The PySide
  teardown workaround in `conftest` hard-exits at session finish, which discarded
  pytest's entire terminal summary; it now prints it first.
- **The dialog auto-centring filter no longer keeps a registry of dialogs.** It tracked
  which dialogs it had already placed in a `weakref.WeakSet`, which measures the wrong
  lifetime: a weakref is attached to the *Python wrapper*, so the entry disappeared when
  Python stopped referencing the dialog — not when Qt destroyed it. Whenever the C++ side
  went first (a parent deletion, `deleteLater()`), the entry silently persisted for a
  dialog that no longer existed, which is the stale-bookkeeping failure the WeakSet had
  been introduced to fix. The mark now lives on the dialog itself as a Qt dynamic
  property, so it is born and destroyed with the thing it describes and there is no
  registry to go stale, nothing to invalidate, and no address to be recycled.
- **The main window's first-run prompt was scheduled with a timer that outlived the
  window.** `QTimer.singleShot(0, self._maybe_offer_first_run_setup)` keeps the callback
  alive independently of the window, so the window can never be freed until it fires —
  and if the window's C++ side goes first, the timer fires anyway, against freed memory.
  It now passes the window as the timer's context object, which ties the callback to the
  window's lifetime. The comment claiming it "never fires in tests" was false: a
  zero-timer fires on any `processEvents()`, of which the suite makes about twenty-two.
- **The window teardown used in tests now lives in one place** (`conftest.stop_window_threads`)
  and joins all seven of the window's QThreads, not four. A second copy had diverged and
  stopped joining the MusicBrainz worker thread, so windows were destroyed with a QThread
  still running — which aborts the process during a later test's garbage collection, in
  an unrelated file.

### Changed
- **CTDB's "no match" no longer claims your rip differs from the database.** We test
  one alignment; CTDB itself sweeps ±5879 samples because offset-shifted pressings
  are routine, so the old wording was a positive inaccuracy claim drawn from 1 of
  ~11,759 valid alignments. Both the results pane and the verdict message now say
  what was actually measured.
- **Settings and the User Guide said CTDB verification was off by default. It is on**
  — so every rip sends the disc's table of contents to an external service, and the
  two places a user would check to find that out both said it didn't.
- Three stale or impossible strings: a scan error offered "switch to the cyanrip
  backend in Settings" (there is no such setting — cyanrip is the only backend), the
  uninstall dialog labelled the legacy `whipper.conf` as "your drive calibration"
  (the real offset lives in Platterpus's own config), and the guide described the
  *Archival exact* goal as adding CTDB verification the other preset already does.
- `mypy` no longer ignores missing imports globally. That flag let the type gate
  collapse silently — an unresolvable PySide6 turned every Qt class into `Any` while
  mypy still printed "Success". Only `musicbrainzngs` and the build-generated
  `platterpus._build` are exempt now, per module, and six zero-cost strictness flags
  are enabled (`disallow_subclassing_any` is the tripwire that makes the collapse
  fail loudly).

*Found by an adversarial review of the v0.5.12 EAC-layout work — five independent
reviewers, each finding then handed to a separate verifier told to refute it. CI was
green on all ten checks at the time.*
- **`Make use of C2 pointers` could claim C2 was used when it only was available.**
  cyanrip's line reports what the *drive* can do ("%s by drive"); EAC's row asks what
  the *rip* did. "unsupported" still earns a truthful `No`; an affirmative capability
  is now unknown rather than a fabricated `Yes`.
- **`Command line compressor` named the `flac` binary, which did not encode the
  audio** — that version comes from the host dependency probe, while cyanrip encodes
  in-process via libavcodec. It contradicted the very next row.
- **The `Filename` row rewrote cyanrip's U+2236 colon**, printing a path that does not
  exist on disk. The disc *title* still shows the real colon (a fact about the disc);
  the filename now shows what is actually on the filesystem.
- **`Track 10`–`Track 14` were mis-aligned** (`Track  14`); EAC right-aligns to width 2.
- **Rows asserted from cyanrip's behaviour** (`Delete leading and trailing silent
  blocks`, `Null samples used in CRC calculations`, `Used interface`) were rendered
  over logs cyanrip didn't write. They are now gated on the actual backend.
- **`Read mode` defaulted to `Secure` for any paranoia level it didn't recognise** —
  now an allow-list, unknown otherwise.
- **The read-stability caveat printed *after* `End of status report`**, which in EAC
  terminates the report. It now sits inside it.
- **Both status counts are padded to width 2**, as EAC does.
- **A single track without sector data deleted the entire TOC table** (a CD-Extra data
  track would do it). Unmeasured cells are now marked; the other rows survive.
- **A track with no number collapsed the whole log to the stub** via a format spec.
- **The parser could raise `ValueError`** on a >4300-digit sector number, violating the
  never-raises rule; and the new C2 branch reassigned the function's own `text`
  parameter — the exact trap a comment 25 lines below warns against.
- **`Pre-gap length` is now rendered** from the sector data the parser captures (the
  field was added and never read).
- The unfillable-row label reads `(not reported by the ripper)`; it named cyanrip
  even on logs cyanrip didn't write.
- **`Fill up missing offset samples with silence` was derived as the complement of
  the overread flag.** Those are two independent EAC checkboxes; the trick only
  happened to work for cyanrip. It now reads cyanrip's actual overread *mode* text.
- **`Gap handling` said `(not reported)` although cyanrip reports it** — its `Gaps:`
  section is now parsed (`None signalled` on the reference disc).
- **`All tracks accurately ripped` could be announced with a track missing.** The
  count only sees tracks that produced *some* result, so a track that failed outright
  was invisible to it.
- **A selective rip presented a partial table as the disc's TOC.** With per-track
  selection a 4-row table appeared under EAC's header, where EAC always prints the
  whole disc. It is now labelled `(partial — N of M disc tracks …)`.
- **A securing pass cut short left no trace.** Found by hardware run 4: closing the
  window 26 minutes into the `-Z` re-read of tracks 3 and 5 produced
  `secure_rerip.engaged: true` with an empty `retried_tracks` and nothing saying the
  pass was interrupted. (The audio was unaffected — the re-rip works in a temp
  directory and only swaps on success.) The report now carries an explicit
  `interrupted` flag.
- **The output-format block still spoke for cyanrip on other rippers' logs.** The
  three archival-header rows were gated on the backend; this block sat one lower and
  told a whipper rip that "cyanrip encodes in-process via libavcodec". Same gate now.
- **The backend gate was a substring test**, so `not-cyanrip 1.0` and
  `whipper (cyanrip-compatible)` inherited cyanrip's asserted behaviour. It anchors
  to the start of the creator string now.
- **Seven more `int()` call sites could raise straight out of the parser** — every
  numeric cyanrip field except the three sector ones (read offset, paranoia counts,
  track number, rip count, both AccurateRip confidences, error count). CPython refuses
  a >4300-digit conversion, so a corrupt log crashed the parse. All now degrade to
  unknown with a logged warning, and the boundary is pinned per-field.
- **A saved log re-parsed to the DISCARDED CRCs.** Platterpus appends a swap addendum
  when the auto-fix replaces a track's file, and its own text says those CRCs
  supersede — but nothing read it back, so `parity.track_copy_crcs` (and the
  `--compare` path, and any third-party tool) got CRCs describing bytes that are not
  on disk. The GUI never hit this because it patches from live worker state. The
  parser now honours the addendum.
- **`_read_stability_line` crashed the whole log to a stub** on a mix of `str`/`None`
  track numbers (`sorted()` over incomparable types) — one bad track took the document
  with it.
- Padded, value-less `Device model:` / `Ripping finished at` / `Paranoia level:` rows
  captured a lone space, rendering an empty row instead of the honest label.
- The parser property test could not reach any of the new branches, so their
  never-raises guarantee was untested; the corpus now includes them, plus a
  4400-digit sector and inverted `Start`/`End` geometry.

*The EAC-layout work below was prepared as v0.5.12 on 2026-07-27 and never
tagged; the audit batch above landed in the same release, so both ship together
here.*

*The EAC-compatible log, checked against a real EAC log of the same disc rather
than an idea of the format — plus the fitness test and CI-gate fix from the same
batch.*

### Added
- **The EAC-compatible log now really looks like an EAC log.** Checked against a
  genuine Exact Audio Copy V1.8 log of the same disc on the same drive, not
  against an idea of the format. New: the **`TOC of the extracted CD` table**,
  derived from the per-track sectors cyanrip reports and **byte-identical** to
  EAC's — values and column alignment both; the **`Artist / Album`** disc line;
  the full archival header (`Read mode`, `Utilize accurate stream`,
  `Make use of C2 pointers`, `Fill up missing offset samples with silence`,
  `Delete leading and trailing silent blocks`, `Null samples used in CRC
  calculations`, `Used interface`, `Gap handling`); the output-format block; and
  the end-of-rip **status report in EAC's own wording** (`N track(s) accurately
  ripped` … `End of status report`) in place of our own phrasing.
  Rows cyanrip genuinely doesn't report say `(not reported by cyanrip)` — never
  a guess, never a silent omission. The attribution header and checksum footer
  stay deliberately un-EAC-like: layout is parity, provenance would be forgery.
- **Accuracy versus EAC is determinable from the two logs alone.** Pinned as a
  test: `parity.compare_logs` reads a real EAC log and ours and pairs all 14
  tracks with no other input. Doing so surfaced a real result — with v0.5.11
  reporting the *shipped* read, the reference rip now matches EAC on **13 of 14
  tracks** (was 12); the auto-fix's re-read of track 5 converged on exactly the
  bytes EAC got. Only track 3, which has never read the same way twice on this
  drive, still differs.
- The parser now captures the disc's album/artist, cyanrip's `C2 errors:` and
  `Paranoia level:` lines, and each track's start/end/pre-gap sectors — the data
  behind the rows above.
- **A fitness test that guards the "surfaces disagree" bug class.**
  `tests/test_surface_consistency.py` renders one `RipLog` through the
  EAC-compatible log, the JSON report and the verdict banner, then asserts they
  agree: identical per-track CRCs, one answer to "how many tracks are proven",
  offset-variant tracks never called absent *or* exact, a non-reproducible track
  flagged everywhere, and an interrupted rip declared in the durable log. Four of
  the last week's defects were one bug — a fact reaching some surfaces and not
  others — and each was invisible to unit tests because every surface was correct
  by its own lights. Each assertion is mutation-checked against the defect it
  exists for.

### Fixed
- **CI's changelog gate could fail a change that satisfied it.** Both of the gate's
  checks piped a producer into `grep -q` under `set -o pipefail`: `grep -q` exits the
  moment it matches, the producer then dies of SIGPIPE, and pipefail reports the
  pipeline as *failed* — so a match read as "no match". It only bites once the
  producer outruns the pipe buffer, i.e. on a long commit range or a big diff, which
  is exactly when these checks matter. It silently ate a legitimate
  `[skip changelog]` opt-out (PR #99), and the `CHANGELOG.md`-was-touched check had
  the same latent bug in the opposite direction — it could have failed a PR that
  *did* update the changelog. Both now read from a here-string, which has no producer
  process to signal. (`media-guard` and `tests-touched` were already safe: they
  capture grep's full output rather than short-circuiting.)

## [0.5.11] — 2026-07-26

*One fix, from the third hardware run: v0.5.10 completed half of a fix and the other
half turned a missing proof into a false one.*

### Fixed
- **A re-ripped track's CRC named the file it wasn't.** Found by the third hardware
  run, and the more serious half of the v0.5.10 fix: when the auto-fix re-reads a
  track and swaps the improved copy into the album, the album's whole-disc `.log`
  still describes the *first* pass — so the EAC-compatible log and the JSON report
  printed the **discarded** read's Copy CRC beside the shipped file's name (track 3
  showed `52DFDF7D`; the file on disk was `3D8FCF0C`), and v0.5.10's new
  Test-and-Copy note decorated that wrong CRC with a convergence proof. The same
  applied to the per-track AccurateRip verdict, which is a statement about specific
  bytes. Platterpus now keeps the re-rip's own parsed record and folds its measured
  fields — CRC, AccurateRip results, read counts, status — over the first pass, so
  every surface describes the audio actually on disk. Identity fields never move,
  and a field the re-rip's log didn't report can't erase a real one. cyanrip's log
  already carried a written swap addendum saying exactly this; our own renderings
  now agree with it.

## [0.5.10] — 2026-07-26

*Both fixes come from the **second hardware run**, and both are the same shape as
v0.5.9's worst defect: Platterpus learned something after cyanrip wrote its log and
never told the renderer. One added proof we had earned; one added a caveat we had
measured.*

### Fixed
- **A re-ripped track's Test & Copy proof never reached the log.** Found by the
  second v0.5.9 hardware run: the album's whole-disc `.log` records only the
  *first* read pass, so a track the per-track auto-fix re-read with `-Z N` — whose
  re-reads *agreed*, which is exactly EAC's Test & Copy evidence — was still
  rendered with a lone `Copy CRC`, and the JSON report's per-track record
  contradicted its own `read_speed.retried_tracks` entry that said
  `converged: true`. The auto-fix's result is now folded back into the parsed log,
  so the Test/Copy pair appears where it was earned. Only a track that both
  converged *and* was swapped in is marked — a re-read that never made it into the
  album leaves the shipped single-read bytes described as exactly that.
- **A track whose re-reads disagreed no longer reads as clean in the log.** The
  same run's track 3 was re-read and *no two reads agreed*, yet its EAC-compatible
  log block was indistinguishable from a clean track's — cyanrip's own health line
  says "No errors occurred" even then, so the durable text artifact was more
  reassuring than the warning the app had already shown on screen. Such a track now
  carries an explicit *"re-reads did NOT agree — this read is not confirmed
  reproducible"* note on its CRC line, plus a whole-disc `Read stability :` line
  naming the affected tracks. Measured only: a track nobody re-read is unchanged.

### Changed
- `docs/eac-parity.md`: the cache-defeat row still described the field
  as permanently `(unknown)` (KDD-25) — superseded by the measured verdict
  (KDD-29) — and the CRC row predated the Test & Copy rendering. Both corrected.

## [0.5.9] — 2026-07-26

*Everything in this release was found by the **first hardware run of v0.5.8**. Eight
defects, three of them honesty defects — a log that said tracks weren't in
AccurateRip when they were, a warning phrased as reassurance, and an interrupted rip
attested as complete. The v0.5.8 features work; these are the rough edges only real
hardware could expose.*

### Fixed
*All found by the first v0.5.8 hardware run (Bazzite + BDR-209D, 2026-07-26).*
- **The cache-defeat probe timed out before it could finish.** The budget was 90
  seconds; `cd-paranoia -A` needs minutes on a real drive (a seven-point seek/read
  timing sweep — one seek measured 3.7 s — then the full cache-behaviour analysis),
  so the app reported an honest but useless "could not be determined" for a drive
  whose analysis actually succeeds. Raised to 10 minutes, and the reference drive's
  real `-A` output is now a committed test fixture.
- **An inconclusive cache result now says *why*.** "cd-paranoia isn't installed",
  "the analysis ran too long", and "it ran but didn't report a verdict we
  recognise" were all shown as the same undiagnosable "could not be determined";
  each now names the actual problem and what to do. When the verdict is unknown the
  captured output is written to the log, so the next occurrence diagnoses itself.
- **"Finished with issues." after a *successful* cache analysis.** The wizard's
  success test was "did we get a read offset", and cyanrip has no offset finder —
  so every cyanrip cache-only run, including a perfect measurement, announced a
  failure (screen readers heard it too). It now reports on what actually ran.
- **The EAC-compatible log wrongly said offset-variant tracks weren't in
  AccurateRip.** A track matching only the +450 offset-variant pressing fell
  through to "Track not present in AccurateRip database" — factually false (the
  real rip's tracks 3 and 5 matched at confidence 200) and contradicting both the
  verdict banner and the JSON report built from the same data. It now reports
  "matched an offset-variant pressing — partially accurate", the same wording every
  other surface uses, and still never claims an exact match.
- **`Overread into Lead-In and Lead-Out` rendered "(unknown)"** even though cyanrip
  states the mode outright; the log parser never read that line. Now parsed — and
  keyed on the *mode* line, not the frame count, which is printed identically
  whether overread is on or off.
- **A drive whose cache can't be defeated was described reassuringly.** That result
  means re-reads may not reach the disc — the one genuinely worrying outcome — but
  it read "this drive doesn't cache audio, so Platterpus doesn't need to read around
  a cache". It now warns, and explains that AccurateRip/CTDB still prove the audio.
- **An interrupted rip produced a log that read as a complete one.** A
  force-stopped 14-track rip rendered as 13 tidy "Copy OK" blocks with an empty
  conclusive section and a *valid* integrity checksum — a self-attested archival
  record of a clean, complete 13-track rip that never happened. The log now carries
  an `*** INCOMPLETE RIP (cancelled) — this log covers 13 of 14 disc tracks ***`
  banner (above the checksum, so it can't be stripped without breaking it), and an
  absent end-of-rip summary is stated rather than left silently blank.
- **Overread was still missed on negative-offset drives.** cyanrip labels the line
  `Underread mode:` when the read offset is negative, so the fix above would have
  kept reporting "(unknown)" for exactly those drives. Both labels are now matched.

## [0.5.8] — 2026-07-24

*The EAC-parity release: each remaining gap closed with equal-or-stronger rigor,
honestly labelled as Platterpus's own — never forged to look like EAC.*

### Added
- **Read offset auto-confirmed on your drive by AccurateRip.** When a rip
  matches the AccurateRip global consensus, the read offset it used is proven
  correct on *your* actual drive — so Platterpus now records that and promotes
  the offset's provenance to **confirmed** (the disc panel's Read-offset line
  shows "confirmed — two independent sources agree"). This is the honest,
  equal-or-stronger analogue of EAC's Key-Disc offset check: stronger because it
  re-confirms on every matching rip, not just once against one disc. Only a real
  match records it, and only when an explicit offset is applied. See PLANNING
  KDD-31. (A from-scratch offset *finder* for drives not in the AccurateRip list
  remains future work — see the cyanrip soft-fork roadmap.)
- **EAC-style Test & Copy verification.** cyanrip's secure re-read (`-Z N`,
  "re-rip until N reads' checksums agree") is the two-reads-agree guarantee EAC's
  Test & Copy provides. The EAC-compatible log now renders a track confirmed by
  ≥2 agreeing reads as a matching **Test CRC** / **Copy CRC** pair (with an honest
  note naming how it was confirmed); a single-read track still shows only a Copy
  CRC — no fabricated second read. A new Settings toggle, **"Verify every track
  with a second read (EAC-style Test & Copy)"** (off by default), reads *every*
  track at least twice for a whole-disc Test & Copy, instead of only re-reading
  tracks that missed AccurateRip. See PLANNING KDD-30.
- **Measured cache-defeat verdict (Set up drive → Analyse cache).** cyanrip
  reports no drive-cache line, so the EAC-compatible log's "Defeat audio cache"
  has read "(unknown)". Platterpus can now *measure* it honestly with
  `cd-paranoia -A` — libcdio's own copy of cyanrip's read engine, so its cache
  self-test speaks for the actual rip's reads. The Set up drive wizard offers an
  "Analyse cache" action (a disc in the drive is needed); the measured Yes/No is
  recorded per drive, shown in the disc panel's new "Cache defeat" row, and
  folded into the EAC-compatible log + JSON report — so the log carries a
  measured verdict instead of "(unknown)". Never fabricated: an inconclusive
  probe stays "(unknown)". This is the equal-or-stronger, honestly-labelled
  analogue of EAC's cache field (same principle as the log checksum). `cd-paranoia`
  is a new optional dependency (installed + exported by the setup wizard as a
  final, non-blocking step); absent, ripping is unaffected and the verdict stays
  unmeasured. See PLANNING KDD-29.
- **The EAC-layout companion log now carries its own integrity checksum.** The
  optional `<name> (EAC-compatible).log` ends with a Platterpus checksum line —
  a plain SHA-256 of every byte above it — that is *at least as strong as EAC's*
  log checksum and **honestly labelled as ours, never EAC's**. EAC's footer is a
  SHA-256 obfuscated with a fixed secret key so only its own Logchecker can
  verify it; ours uses the same hash primitive *openly*, so anyone can reproduce
  it with a standard tool and no secret (`head -n -1 "<name> (EAC-compatible).log"
  | sha256sum`) — same cryptographic strength, more transparent to check, and
  never mistaken for EAC's signature. The existing "NOT signed by Exact Audio
  Copy" disclaimer is unchanged; we still never emit EAC's own
  `==== Log checksum <hex> ====` marker. See PLANNING KDD-28.

## [0.5.7] — 2026-07-24

### Added
- **Choose which tracks to rip.** The track table has a leading **Rip?**
  checkbox column (every track ticked by default), and right-clicking one or
  more highlighted rows offers **Rip only these** / include / exclude / select
  all / none. Start rips whatever's ticked — all ticked means the whole disc,
  a subset becomes cyanrip's `-l`. A zero-selection start is blocked with a
  clear message. Tags and AccurateRip stay aligned because track numbers are
  absolute.
- **Every setting now has a hover tooltip, enforced.** Filled the last few
  Settings controls that lacked one (output/working directory, disc template,
  the unknown-disc templates, Picard, metaflac path) so hovering any control
  explains it the way the User Guide does. A new test ties tooltip coverage to
  the guide-currency classification: a setting documented in the guide must also
  carry a tooltip on its control (and vice versa), so the two can't drift apart.
- **Opt-in: also re-read offset-variant (partially accurate) tracks** (Settings,
  off by default). An offset-variant AccurateRip match confirms a pressing but
  does **not** prove the read is reproducible — real hardware showed a track
  offset-variant-matching two rips with *different* audio each time. When on,
  those tracks get the same secure `-Z` re-read as an AccurateRip miss, so an
  unstable one converges on a stable, repeatable read. Off keeps today's fast
  path (offset-variant accepted on the first read); it only costs time on discs
  that actually have offset-variant tracks. See PLANNING KDD-27.

### Fixed
- **AppImage build pins the bundled CPython version.** `python-appimage` was
  grabbing the newest CPython base image, which had become a 3.15 *beta* that no
  PySide6 wheel supports — the release build aborted with "No matching
  distribution found for PySide6". The build now pins a stable, PySide6-supported
  interpreter (3.12, overridable via `PLATTERPUS_PYTHON_VERSION`), so a new
  upstream Python beta can't break the build.
- **"Open rip folder" now works during a rip and after a cancel/partial rip.**
  Previously the button only became usable once a rip *finished successfully*;
  a cancelled or failed rip left `set_log_path(None)`, which disabled the
  folder and log buttons even though the (partial) output folder existed on
  disk. The in-progress folder is now tracked separately from the last
  finished rip, so Open-folder and View-log stay reachable from the moment a
  rip starts through cancel, freeze, or failure. (Real-hardware bug: after a
  force-cancel, "opening the rip folder with the button did not work.")

### Added
- **Real-time logs and access buttons during a rip.** "Open rip folder" and
  "View log" are enabled from the moment the rip starts (not just on success),
  and "View log" opens the live application log (`log.txt`) while the rip is
  running — so if the ripper freezes you can still reach the logs immediately
  instead of after it (never) returns. cyanrip's own output is now mirrored to
  the app log line-by-line under Debug logging, so a frozen run leaves a
  real-time trail on disk.
- **Rip stall / liveness indicator.** A GUI-thread watchdog notices when the
  ripper has produced no output for a while (default 45 s) and shows a warning
  banner ("the ripper has gone quiet — it may be working on a difficult track,
  or it may be stuck") instead of the progress bar silently sitting at, e.g.,
  99.47 %. When overread is enabled the banner names it as the likely cause,
  since overread can hang some drives on the disc's lead-out. The banner clears
  itself the moment the ripper produces output again.
- **The disc panel's Drive line now identifies the exact drive** — make, model,
  **firmware revision**, and device node (e.g. "PIONEER BD-RW BDR-209D ·
  firmware 1.51 · /dev/sr0"), not just the `/dev` path. The firmware revision
  is the identifier a hardware bug report needs, and the line stays
  copy-selectable so it can be pasted straight in.

### Changed
- **Removed the per-track progress bar in the track grid.** It duplicated the
  current-task bar in the progress pane below — same percent shown twice — so
  the grid's Status column is back to plain "⟳ Ripping" / "✓ Done" text and live
  progress lives in the one two-tier bar (overall + current task). (Real-user
  feedback: "what is the point of having two progress bars show the same?")
- **Filled the in-app User Guide's gaps** (Working directory, Read speed, the
  desktop-completion notification, the EAC-compatible log, back-cover/booklet
  art) and added a test that fails if any future setting ships undocumented —
  every `Config` field must now be either documented in the guide or explicitly
  marked internal, so the guide can't silently fall behind the settings again.

## [0.5.5] — 2026-07-21

### Security
- **Release-signature verification in the in-app updater (Ed25519 / minisign,
  fail-closed, ships dormant).** SHA-256 proves a download's integrity but not
  its authenticity — a compromised release channel could swap both the AppImage
  and its `.sha256`. The updater now also verifies a `minisign` signature made
  with a key the maintainer holds **offline** (so a CI compromise can't forge
  it): a new `update_signing.py` parses the `.minisig` and Ed25519-verifies it
  via `cryptography`, and the updater refuses to install a release whose
  signature is missing or invalid. It's **armed** only once a maintainer public
  key is baked into `update_signing.PUBLIC_KEY_B64`; until then the updater is
  SHA-256-only exactly as before, so this release changes nothing user-visible.
  Adds `cryptography` as a dependency (floored at `48.0.1`, the fix for advisory
  GHSA-537c-gmf6-5ccf, so the CI `pip-audit` gate stays green). See
  `docs/release-signing.md` (the offline signing ritual) and PLANNING KDD-26.
- **Reproducible-build dependency hash-pinning (opt-in plumbing).** The AppImage
  build can now pin the exact *bytes* of every bundled third-party dependency,
  not just their versions: `build/lock-requirements.sh` writes a hash-pinned
  `requirements.lock`, and when that lock is present `build_appimage.sh`
  re-downloads the closure with `pip --require-hashes` (aborting on any
  mismatch) and installs python-appimage's per-line deps offline from the
  verified wheelhouse. Additive — no lock means the previous version-pinned
  online install, unchanged. Full-AppImage reproducibility validation is a
  real-build step for the maintainer; the sandbox can only verify the wheel.

### Added
- **View the rip's cue sheet from the results pane.** cyanrip writes a `.cue`
  (the disc's track/index map) beside the `.log` on every rip; a **View cue**
  button now sits alongside View log / View report and opens it in the in-app
  read-only viewer. It's enabled only when a cue is actually present, and — like
  the other output buttons — it follows the album folder if a library move
  relocates the rip. (PLANNING KDD-13's "small P1 addition".)
- **MP3 VBR quality is now a Settings control** (Settings → "MP3 VBR quality",
  0–9, default 0). The `mp3_vbr_quality` config field was already plumbed
  through the transcode adapter (ffmpeg `-q:a N`, the same as lame `-V N`) but
  fixed at the best-practice `-V0`; it now has a spinbox that enables only when
  the output format is MP3. Higher numbers trade quality for smaller files;
  the FLAC master stays lossless regardless.

### Fixed
- **README/SECURITY front-door drift after v0.5.0** (maintainer-reported): the
  README status banner still read "v0.4.x" with the old 1,600+ test count; the
  settings section still called force-overread "a re-openable cyanrip `-x`
  task" (it shipped in v0.5.0 as the Overread toggle — and the real flag is
  `-O`, `-x` never existed); the v0.5.0 features (Overread, "Move finished
  rips to", the live per-track progress bar) were missing from the settings
  list, the first-run walkthrough, and the EAC-parity overread row; and
  `SECURITY.md` still declared `v0.4.x` the supported series.

- **EAC gap-handling parity closed as already-satisfied.** A 2026-06-14 note
  flagged gap handling as a possible parity lever ("we set no gap mode"). Re-
  verified against cyanrip's own README and source (0.9.3.1 + master): cyanrip's
  default *is* EAC's ("identical to EAC's default behaviour"), which is how the
  committed 12/14 audio-parity proof matched — so there is no audio gap and no
  knob to add (cyanrip's `-p` is a per-track override whose only archival-safe
  value is the default we already use; `drop` deletes audio, `track` renumbers
  tracks). The docs that implied an unset gap mode (`test-plan.md`,
  `eac-parity.md`) are corrected, the `-p` contract is recorded in
  `dependency-contracts.md`, and the TASKS item is closed. The remaining
  `INDEX 00` cue-metadata difference stays tracked separately (PR #115 route).

### Changed
- **Removed the vestigial `fallback_tiers` field from `DependencySpec`.** The
  manager-driven tier cascade it fed was removed long ago (TD-3); nothing read
  the field, so it's deleted (with its one construction site and the test
  helper's parameter). The `tier` label stays — it's now formally documented as
  the descriptive AUTO/QUEUED/MANUAL summary of how a dep resolves (routing keys
  on `from_setup_wizard`/`install_command`, not on `tier`), rather than a field
  "pending removal." Contributor-facing; no behaviour change.

### Documentation
- **Housekeeping sweep (2026-07-21):** logged the pre-release dependency review
  for v0.5.0 (no new dependencies — the whole cycle is stdlib + the existing
  PySide6 pin); closed three stale whipper-era backlog rows in `TASKS.md` (the
  dead "upstream whipper bug fixes" row — no upstream to route to since KDD-18 —
  and the two whipper-CLI drive-setup doc rows, folded into the single
  hardware-gated proof queue); and re-verified the upstream-PR "verify-before-
  you-invest" checklist against live GitHub: cyanrip **PR #115** still open
  (mid-revision, last activity 2025-11-28) and libcdio-paranoia **#3** still open
  with zero comments.
- **Doc version stamps can no longer lag the release they ship in.** Every doc
  revised during the v0.5.0 cycle still carried a v0.4.24 footer, because the
  convention bumps stamps to the `__version__` current *at commit time* —
  always one release behind what the change ships in, with nothing enforcing
  the convention at all. All 44 cycle-touched docs are restamped v0.5.0, and a
  new gating test (`tests/test_doc_version_stamps.py`) closes the loop: every
  tracked doc carries exactly one footer, no footer may claim a future
  version, and any doc changed since the latest release tag must be stamped
  with the current `__version__` — so the release-prep version bump itself
  forces the cycle's restamp. The CI `test` job now checks out full history so
  the tag diff works there; the release checklist (CLAUDE.md) gained the
  restamp as step (3), and `docs/README.md` documents the enforced rule.

## [0.5.0] — 2026-07-21

### Added
- **Overread toggle (Settings → Overread, off by default)**: ask the drive to
  read the disc's outermost samples from the lead-in/lead-out (cyanrip's `-O`)
  instead of writing them as silence — the last EAC parity-gap Settings knob,
  rebuilt cyanrip-native (the whipper-era toggle died with whipper, KDD-18).
  Off matches EAC's baseline setting and how the committed 12/14 parity proof
  matched; upstream's "may freeze if unsupported by drive" caveat is surfaced
  in the tooltip and User Guide.

- **Auto-move finished rips to a library folder** (Settings → "Move finished
  rips to", empty = off): a successful rip's album folder is filed into the
  library only after every post-rip check has settled — tagging, cover art,
  transcode, the whole verification suite, checksums, and the report write all
  finish first, so nothing ever verifies or hashes a file mid-move. Collisions
  land in a "(N)" sibling (never overwritten), the View log / report / folder
  buttons repoint to the new home, and the "you've ripped this before"
  comparison now searches the library too. A failed move just leaves the rip
  in the output folder and says so — it never looks like a failed rip.
- **Live per-track progress bars**: the track table's Status column now shows
  a real progress bar (percent visible in the bar) on the row currently being
  ripped, driven by the same live percent as the bottom progress bar; a
  finished track's bar is replaced by "✓ Done" (status stays text for screen
  readers — the bar is decoration, never the only signal).
- **Cross-filesystem naming warning (Settings, warning-only)**: a naming
  template whose literal text would not copy cleanly to Windows or an
  NTFS/exFAT drive (reserved characters, reserved device names like `CON`,
  trailing dots/spaces) now shows a live warning in the Settings validation
  banner — never a block, since all of it is legal on the Linux target.
  Closes the last open item of the 2026-07-08 trust audit
  (maintainer-approved); hazards inside tag *values* remain a documented
  limitation (the ripper owns naming).

### Fixed
- **cyanrip flag-letter corrections in the docs (a shipped-bug near-miss)**:
  `docs/dependency-contracts.md`, TASKS.md, and the parity scorecard claimed
  cyanrip's overread flag is `-x` — **`-x` does not exist in cyanrip's getopt
  at all** (verified against the deployed 0.9.3.1 *and* master; wiring the
  documented letter would have aborted every overread rip — the real flag is
  `-O`, now pinned by a regression test). The same verification corrected the
  `-f` description: it is a real "find drive offset" mode (deliberately unused
  since the 2026-06 mis-scrape incident), not "force-overread" as three code
  comments and the contracts doc said; a vetted re-integration is now a
  tracked maintainer call in the feature backlog.
- **Accessibility: focus-safe live announcements + the full
  keyboard-reachability sweep** (UX gap #4's remaining half, closing the gap —
  a live screen-reader session on real hardware is the one confirmation still
  owed). New `ui/accessibility.py` `announce()` helper (Qt announcement
  events — the desktop `aria-live`; feature-detected, never raises, never
  moves focus) now speaks the rip status per *phase* (throttled — never
  per-percent), the AccurateRip verdict banner, the read-effort warning, the
  CTDB line, the re-rip comparison, disc-identification outcomes, the
  wrong-offset guard warning, setup/uninstall wizard steps and outcomes,
  per-dependency install rows, the Settings validation banner, and
  copy/save confirmations. Keyboard fixes: the copyable disc-ID values and
  the drive-diagnosis fix command are now tab-reachable and
  keyboard-selectable (Qt's keyboard-selectable labels default to
  click-only focus), the accuraterip.com lookup link is keyboard-followable,
  anonymous Settings fields/Browse buttons and the release-candidates table
  gained accessible names, and every prominent button carries a unique
  Alt+letter mnemonic (uniqueness pinned by test). Pattern documented in
  `docs/architecture.md` §3.8.
- **`docs/manual-ctdb-repair.md`** — the manual CUETools/`ctdb-cli` CTDB
  repair workflow (the power-user escape hatch for a track that stays
  "partially accurate (450)" after `-Z` re-rips) that the feasibility and
  parity-investigation docs have recommended documenting since 2026-06-28.
  Assembled strictly from the existing research record; steps never executed
  on project hardware are marked *(unverified)*; in-app repair stays parked
  (KDD-14 Phase 2).
- **cyanrip upstream-contribution kit** (`scripts/cyanrip/`, PR #80,
  2026-07-09; bullet added retroactively under the 2026-07-21 strict
  `[skip changelog]` ruling): a verified, dry-run-first patcher for the
  colon fix (`apply-colon-fix.py`, unit-tested), fork/build scripts, the
  canonical paste-ready upstream issue/PR bodies, and the ASan/UBSan-proved
  C harness.

### Fixed
- **mypy 2.3 compatibility for the two Qt typing seams**: mypy 2.3 stopped
  accepting `track_table`'s bare `QModelIndex | QPersistentModelIndex`
  assignment as a type alias and `main_window_shared`'s conditionally
  re-assigned `_SeamBase` variable as a base class — the `typecheck` CI job
  would go red on its next cold-cache run. An explicit `TypeAlias` marker and
  the import-as conditional-base form restore a clean `mypy` with zero runtime
  change (MRO/metaclass verified identical).

### Changed
- **TASKS.md's "⭐ START HERE" queue re-ranked around what is actually open**
  (docs-audit consolidation plan, maintainer-approved): the live queue now
  leads with trust hardening, the prepared cyanrip soft-fork PRs, the
  consolidated hardware-gated proof list, the docs backlog, and the UX
  remainder; the completed 2026-06-09 plan is preserved as ranked history
  with its numbering intact (other text cites "current-plan item N").
- **UX gap backlog single-homed** (docs-audit consolidation plan):
  `docs/ux-design-principles.md`'s ranked gap table is the canonical record
  (code comments cite its numbering); the TASKS.md item that had drifted from
  it is now only a per-gap tracking checklist linking there.
- **Remaining single-home doc cleanups applied** (docs-audit consolidation
  plan): `docs/eac-parity.md` now points at architecture §3.7 for
  the two-artifacts rationale instead of restating it;
  `tests/fixtures/README.md`'s EAC-baseline section is a pointer at
  `output_reference/` plus the UTF-16/`decode_log_bytes` warning;
  `docs/dependency-contracts.md` gained an explicit scope note naming the
  installer/desktop-integration/GitHub-API surfaces it deliberately excludes;
  `docs/architecture.md` §2's layer table gained a "Qt-free domain modules"
  row pointing at PLANNING.md §2 as the canonical per-module map.
- **`cyanrip-fork.md` Part A §9 now states where the 2026 ripper-landscape
  research doc lives** (closing the consolidation plan's last open sub-item):
  it was maintainer-provided session research input, never committed to the
  repo — the project's own record preserves (and corrects) its load-bearing
  claims via the parity scorecard, §9's notes, and KDD-24; if the file
  resurfaces it goes to `docs/archive/` per the compass-artifact convention.
- **The "two corrections to the ripper-landscape doc" condensed to one home**
  (docs-audit consolidation plan): PLANNING.md KDD-24 keeps the full text (the
  designated record); `docs/eac-parity.md` now carries a
  one-line summary + link instead of the duplicated telling.
- **`docs/trust-audit-2026-07-08.md` retired to `docs/archive/`** (maintainer's
  call, completing the audit doc-map): graduation row added to the archive
  index; its still-open items (release signing, dependency hash-pinning)
  remain tracked in the TASKS.md trust-hardening section; inbound references
  retargeted.
- **Strict def-typing (`mypy`) enforced across the entire package** (PRs
  #81–#83, 2026-07-09→20; bullets added retroactively under the same ruling):
  staged in three ratchets — everything outside `ui/` (a zero-code-change
  config tighten), the standalone UI widgets (8 real annotations fixed), and
  finally the `MainWindow` god-object + its five mixins via the new
  runtime-neutral `ui/main_window_shared.py` typing seam (which also fixed
  ~10 real type gaps). No per-module exclusions remain.
- **`[skip changelog]` scope settled — strict** (maintainer ruling,
  2026-07-21): the exemption covers *pure historical-record commits only*;
  contributor/CI-facing changes get bullets like any other change. Wording
  clarified in CLAUDE.md's Commit & PR hygiene and the testing.md Definition
  of Done; the four PRs that had used the broader reading got their bullets
  above.
- **README's duplicate EAC-parity section folded into the top matrix**
  (maintainer-approved): the "Compared to EAC's bit-perfect settings" lists
  restated the capability matrix and point-by-point table from the top of the
  README (the drifted CTDB status had rotted in three places for exactly this
  reason) — the section now points at the matrix, KDD-13, and
  `docs/eac-parity.md`, and the Settings rundown lives under its
  own "Rip settings at a glance" heading.
- **`CLAUDE.md`'s companion-document list slimmed to one-line pointers**
  (maintainer-approved): `docs/README.md` is the canonical annotated index and
  the two lists had already drifted once — the always-loaded anchor now names
  each doc in a line and defers the annotations to the index.
- **`docs/test-plan.md` whipper-era cases rewritten for the cyanrip-only
  reality** (maintainer-approved): Test 3 is now the drive-setup-wizard
  success-screens + auto-vs-manual offset capture (absorbing Test 4, retired);
  Test 8 is the cyanrip parity record with the `-Z` convergence re-rip as its
  open core; Test 10 and step A8 are retired stubs (numbers kept as stable
  IDs); Part B's procedure and parity-variables are single-backend. **New
  Tests 12–14** add the missing hardware rows: the read-speed ladder /
  auto-fix / speed-locked `-S` stack, CD-Extra CTDB TOC handling, and the
  EAC-compatible companion log + goal presets.
- **cyanrip-cluster dedup completed** (maintainer-approved): the soft-fork
  runbook's duplicated issue-body blockquotes are replaced by links to the
  kit's canonical `scripts/cyanrip/issue-*.md` paste files, and the
  upstream-process facts (maintainer contact, style, CI, PR responsiveness)
  now live once, in the roadmap's Process block — the strategy doc §6 and the
  runbook link there instead of restating them.
- **`docs/audit-2026-07-02.md` retired to `docs/archive/`** (maintainer-
  approved doc-map move): its §E remainders were already graduated to the
  TASKS.md Documentation backlog, the archive index gained the graduation
  row, and every inbound reference was retargeted. **The colon-fix proof
  harness moved into the kit** as `scripts/cyanrip/verify-meta-colon.c`
  (the kit is the declared execution layer) with the runbook, test
  docstring, indexes, and PLANNING tree updated.
- **Dependency-review catch-up logged for v0.4.19–v0.4.24** in
  `DEPENDENCIES.md` (maintainer-approved): all pins verified healthy against
  live PyPI — notably mypy is at 2.3.0 upstream, so the `>=1.13,<3` bound is
  now load-bearing — and the per-release dependency changes since the
  2026-07-07 review are recorded.
- **The `build` frontend is now actually pinned `>=1,<2`** in `release.yml`,
  `appimage.yml`, and `build_appimage.sh` (maintainer-approved; the audit
  found `DEPENDENCIES.md` claiming a pin no install site applied — the doc
  row now matches reality again).
- **Two maintainer-approved doctrine updates in `CLAUDE.md`** (2026-07-21
  audit follow-up, both explicitly authorized): Critical Rule #3 now names its
  own scoped, user-approved force-stop exception (approved 2026-05-31, until
  now documented only in `docs/dependency-contracts.md`); and the
  brief-vs-PLANNING precedence rule reads "the brief **as amended by the
  maintainer-approved KDDs** wins on requirements/scope" (matching actual
  practice since KDD-12/KDD-22 — `docs/README.md` updated to match).
- **Full documentation audit (2026-07-21).** Every Markdown doc in the repo was
  audited against the code, CI, and the live tag history — 239 findings, ~160
  fixed in this release's docs commits. The audit record (systemic patterns,
  before→after doc map, open maintainer questions) is
  `docs/archive/audit-2026-07-21.md`; the unexecuted consolidation plan is captured in
  `TASKS.md` → P1 Documentation backlog.
- **`TASKS.md` statuses caught up with shipped reality.** CTDB verify's three
  trackers all still read as open/hardware-gated although the CRC was
  validated 2026-07-07 (v0.4.20) — current-plan item 8 is now marked complete
  and declared the canonical status home, with the other two reduced to
  pointers; the "both backends" hardware-parity item, the whipper parity-
  matrix rows, and the whipper-era Step-5 doc item are marked
  retired/superseded (whipper removed 2026-06-30); the committed cyanrip
  FLAC (12/14) and MP3 (13/14) proofs are now reflected in the matrix; the
  obsolete "don't start P1 until P0 ships" fences, the stale PyPI
  verified-through pins, and the accessibility-pass over-claim (now 🟡 with
  the remaining work named) are corrected.
- **`PLANNING.md` synced with the post-whipper, v0.4.24 codebase.** The §1
  directory tree gained the ~25 files it was missing (docs, scripts incl. the
  `scripts/cyanrip/` kit, `atomic_write`/`build_info`/`rip_compare`/
  `cli_compare`/`drive_media`/`notify`, `ctdb/calibrate`+`diagnose`,
  `ui/main_window_shared`, `dialogs/file_viewer`, `mutation.yml`,
  `SECURITY.md`) with matching §2 one-liners; stale claims corrected
  (make_icon needs a rasterizer not Pillow, real AppImage recipe filenames,
  SettingsDialog widget list, offset gate reads the GUI override only, §5
  "still open" items that shipped 2026-06-09, §7 build-script sketch);
  whipper-era KDDs (02, 07, 11, 13, 15, 17, 23, 24) got dated cyanrip-era
  annotations in the established KDD-13/18 style — original decision text
  preserved as the record.
- **`CLAUDE.md` operations/companion sections brought up to current reality**
  (locked rules untouched): the CI description now lists all seven `ci.yml`
  jobs (incl. the gating `mypy` typecheck, `media-guard`, and `pip-audit` added
  2026-07-08) plus the weekly `mutation.yml` and the `appimage.yml` branch
  builds; the release-asset list now includes the `.zsync` and the provenance
  attestation; the companion-document list gained `SECURITY.md`,
  `docs/mp3-wav-support.md`, and the soft-fork/roadmap companions, and no
  longer restates the KDD count (that lives in `docs/README.md`).

### Fixed
- **Duplicate category headings merged throughout this changelog**
  (maintainer-approved audit follow-up): `[0.4.10]`, `[0.4.5]`, `[0.4.0]`,
  and `[0.2.0]` each carried repeated `### Added`/`### Changed`/`### Fixed`
  headings from incremental edits — now one heading per category per release
  (Keep-a-Changelog form), every bullet preserved in order.
- **AppImage/build/SOP docs corrected; dated records got preservation
  banners.** `appimage-testing.md` now documents the `workflow_dispatch`
  release route (the only one that works from cloud sessions), the `.zsync` +
  PyPI hand-off in the asset checklist, artifact expiry, and the cyanrip host
  stack. `build/python-appimage/README.md` no longer omits `pyproject.toml`
  from the pin-update instruction (following it would have desynced the three
  sources) and describes what the build script actually does.
  `github-workflow-sop.md`'s preface now lists all four CLAUDE.md
  divergences, §7.1 matches the all-PRs squash policy, and the footer credits
  the roadmap for the PR ordering. The research brief, the session-start
  bootstrap, the three 2026-06 archive investigations, and both dated audits
  gained preservation banners / status addenda (bodies unedited) so none of
  them reads as current where reality moved on.
- **`output_reference/` + `tests/fixtures/` READMEs match the committed
  proofs.** The layout matrix no longer marks the committed cyanrip FLAC
  (12/14) and MP3 (13/14) proofs as empty; the whipper row and the three
  `whipper_*` placeholder READMEs are reframed as historical (whipper removed
  2026-06-30 — those proofs can never arrive); the commit policy matches the
  actual "store the text, document the imperfection" practice; the Git-LFS
  advice (never configured) is replaced by the real CC0 + `--no-verify` flow;
  the EAC_wav README records that WavPack shipped; EAC_mp3's "planned
  whipper-path transcode" is the shipped adapter; and `EAC_flac/` — the one
  directory holding the canonical UTF-16 baseline — finally has its own
  README with the don't-re-encode warning.
- **CHANGELOG record repaired against the real tag history.** The lost
  `## [0.3.10]` heading is restored (verbatim from the `v0.3.10` tag's own
  CHANGELOG — its colon-in-tags fix had been absorbed into `[0.4.0]`); the
  `[0.2.0]`/`[0.2.1]`/`[0.0.1]` link definitions no longer point at tags that
  don't exist on the remote (both anomalies annotated inline); the skipped
  `v0.4.3` number is annotated like the v0.2.0 anomaly; the head note now
  names `docs/session-log.md` instead of "the CLAUDE.md session log".
- **cyanrip cluster reconciled (strategy / roadmap / soft-fork / kit).** The
  strategy doc's §8.1 no longer claims dynamic secure re-rip is opt-in/off (it
  shipped on-by-default with no checkbox, 0.4.9), its §10 pointer box carries
  the roadmap's revised support-#115-first headline instead of the superseded
  cdrdao-DO-NOW one, §6 records that the soft fork now exists (with the
  FFmpeg-flag question answered), and the KDD-18 "quote" is re-attributed.
  The roadmap's at-a-glance table and intro now agree with its own 2026-07-07
  update box (cdrdao = fallback), it gained a 2026-07-08 pointer box to the
  two prepared contributions, and the deleted `config.ripper_backend` seam
  claim now names the real `RipBackend` ABC seam. cyanrip's license reads
  LGPL-2.1-or-later consistently across all three docs. The kit's paste files
  are declared the canonical issue/PR text; `cyanrip/` (the local soft-fork
  checkout) is now git-ignored with a note in the kit README, which also
  gained the standard footer stamp and an accurate build.sh description.
- **Research/design docs reconciled with their own outcomes.**
  `eac-parity.md` no longer reads as pending: Part A's
  decision gate records the KDD-24 resolution (option 1 standing, option 2
  shipped v0.4.16, signing permanently closed), Part B's CRC blocker is marked
  cleared (v0.4.20), and the misattributed "CLAUDE.md" ethos quote is
  re-cited. `eac-parity.md` gained a dated Outcome note (13/14
  reached, Track-3 transience confirmed then refined to read-instability, the
  `-Z` hardware gate answered, P1 done) plus superseded-pointers for the
  INDEX-00 route (PR #115 via the upstream roadmap) and the renamed `-Z`
  Settings control. `mp3-wav-support.md` gained a status note (whipper
  removed; ffmpeg is the sole shipped WavPack encoder — as-built annotations
  on the locked decision block rather than rewrites) and its stale
  "still to add"/"Test-plan candidate" parentheticals now record what
  shipped.
- **Reference-doc accuracy sweep (dependency-contracts, ux-principles,
  log-format, CTDB-CRC).** `dependency-contracts.md`: CTDB matches read
  "verified" (CRC hardware-validated v0.4.20, this was the last "experimental"
  holdout); the force-stop section now shows the real device-scoped-first kill
  order (0.4.9, #23); three in-scope invocations documented (ffmpeg PCM
  decode-hash, flac raw decode for the CTDB CRC, `metaflac
  --show-total-samples`); CAA manifest/back/booklet fetches documented; the
  musicbrainzngs contract gained `cdstubs=False` + the TOC-lookup form; the
  recompress argv shows `--silent -f -o <tmp>`. Two stale code comments
  corrected to the 2026-07-01 hardware finding (a speed-locked drive makes
  cyanrip abort on `-S`; the ladder never sends it) and `track_table.py` now
  cites UX principle #10, not #7. `ux-design-principles.md`: principles 2/3/7
  and the gap table match shipped reality (dynamic `-Z` default, goal presets
  shipped, the GUI offset override is the sole authority). `log-format-
  comparison.md`: records the optional EAC-compatible companion log (v0.4.16)
  instead of denying it exists; real parser-test path. `ctdb-crc-algorithm.md`:
  disc-specific back-trim qualifier restored; the `crc32_combine` fast path
  count matches the ±5879 window.
- **`docs/test-plan.md` no longer directs testers at removed whipper
  features.** The whipper-era cases (Tests 3, 4, 8, 10 and step A8) now carry
  explicit ⚠️ SUPERSEDED banners with the cyanrip-era successor flow (their
  full rewrite is tracked in the TASKS.md Documentation backlog); wording
  fixes throughout: the preflight verifies the cyanrip routing, the wizard
  installs cyanrip/flac/metaflac, the uninstaller has two checkboxes, D9/D10
  are cyanrip-native (no "Continue on CD-R" / "Keep going" toggles), the
  fidelity-verdict quote matches the shipped string, Test 1b's as-built
  record matches today's `verify_rip_dir` + on-by-default CTDB toggle, and
  the reporting template is single-backend.
- **`docs/architecture.md` / `docs/testing.md` corrections.** Architecture: the
  §1 diagram no longer claims the GUI queries AccurateRip (cyanrip verifies
  in-rip; the GUI only carries the offline offset list); `build_backend` is no
  longer "the whipper/cyanrip choice"; the unmaintained flag is
  `appimage-builder` (matching Critical rule #1), not `python-appimage`;
  `MbWorker` → `MusicBrainzWorker`; the §3.2 dialog bullet now carries the
  "Dialogs that do blocking work" name CLAUDE.md cites; force-stop/pkill rules
  repointed to `dependency-contracts.md` (they were never in CLAUDE.md); the
  live cyanrip progress regex replaces the inert whipper one. Testing: the
  gating `mypy` typecheck is now in the layers table, the Definition of Done,
  and the dev-extra list; mutation testing is documented as the weekly CI run
  it became 2026-07-08; golden-test guidance reframed around cyanrip as the
  live backend; the supply-chain CI jobs (pip-audit, media-guard,
  tests-touched) are in the layers table and rule 9's backstop list.
- **`docs/README.md` index made complete and current.** The two dated audit
  records (`audit-2026-07-02.md`, `trust-audit-2026-07-08.md`) are now
  indexed; the soft-fork row points at its C proof harness and the
  `scripts/cyanrip/` execution kit; the CTDB-repair row no longer claims the
  CRC gate is still open (cleared v0.4.20); the outside-docs table gained
  `SECURITY.md`, `CHANGELOG.md`, `output_reference/README.md`, and
  `scripts/cyanrip/README.md`; the stamp rule now exempts the paste-ready
  upstream issue bodies. `docs/archive/README.md`: the CTDB Phase-1 spec is
  no longer called "unbuilt", the offset-investigation graduation row credits
  the right modules, and the extraction-guide summary row matches the trimmed
  content.
- **`DEPENDENCIES.md` / `SECURITY.md` corrections.** The mypy row now shows
  the real pin (`>=1.13,<3`) and the package-wide strict gate (the "except the
  Qt UI mixin layer" note — also stale in a `ci.yml` comment — predated the
  2026-07-19/20 strictness completion); the `build` row no longer claims a pin
  that exists nowhere; the mutmut row records the weekly CI run; the Pillow
  tombstone row was removed per its own review instruction. SECURITY.md's
  no-overwrite promise now cites the actual v0.4.22/v0.4.23 overwrite guards
  instead of the unrelated Critical Rule #8, and the file gained the standard
  footer stamp.
- **README caught up with shipped reality.** CTDB verification is no longer
  described as "experimental / CRC fix pending" (it was hardware-validated in
  v0.4.20 — all four stale spots corrected); the container-upgrade example no
  longer suggests `--releasever=41` (below the cyanrip COPR's Fedora-42
  floor); the uninstall one-liner no longer implies AppImage users have a
  `platterpus` command; the pipx section drops the "before the first
  published release" hedge; the release bullet now states the version-bump +
  changelog preconditions and the dispatch path.
- **Documentation: five broken relative links repaired.** Four links in
  `docs/session-log.md` and one in
  `docs/archive/upstream-modification-investigation.md` used repo-root-relative
  targets from inside `docs/`, so they 404'd when browsed on GitHub. Link text
  is unchanged — only the targets were corrected.

## [0.4.24] — 2026-07-09

### Added
- **Re-rip comparison — "you've ripped this disc before".** Platterpus was
  stateless per rip, so it couldn't tell you a re-rip came out *different* from
  the last one. Now, after a rip, it looks for a prior `.platterpus.json` for the
  same disc (keyed on the TOC-derived MusicBrainz Disc ID) and, if found, shows a
  results-pane banner: how many tracks are byte-for-byte identical, which differ,
  and **which rip is the better master** (an exact AccurateRip match beats an
  offset-variant one). The discovery scan runs off the GUI thread. This is the
  automatic version of the by-hand finding that a re-rip's track 3 had silently
  regressed from an exact match to an offset-variant read.
- **`--compare A.platterpus.json B.platterpus.json`** — a terminal CLI that
  prints the same track-by-track comparison (identical / differing / better
  master), plus a best-of-both plan preview when tracks differ. Exit code 1 when
  rips differ, 0 when identical, 2 on a read error.
- **`--assemble-best-of DEST A.json B.json`** — copies, per track, the better of
  two rips of the same disc into a new folder. Strictly non-destructive: the two
  source folders are never modified. Refuses to run across different discs.
- **Per-track read-effort warning.** The report and results pane now flag tracks
  that needed unusually heavy re-reading (or a `-Z` secure re-read that never
  converged) even if they matched AccurateRip — the earliest in-rip hint a track
  may not be reproducible (report issue `heavy_reread`; a results-pane footnote).
- **AccurateRip ↔ CTDB reconciliation line.** When AccurateRip reports "mostly
  accurate" but CTDB reports "no match", a one-liner now explains they're the
  *same* finding (a whole-disc CRC can't match when a couple of tracks differ),
  not two contradictory ones.
- **Offset-variant / "partially accurate" explanations** — a tooltip on the
  affected AccurateRip cells and a User-Guide glossary section, including the
  re-rip caveat (a result that *changes* across rips is a read-stability problem,
  not a pressing difference).

### Changed
- **Rip report schema → v9** (additive): the `rip` block now carries
  `musicbrainz_disc_id` and `cddb_id` (TOC-derived disc identity, the key the
  re-rip comparison uses); each track now serializes `secure_rerip_converged`
  (previously parsed but dropped); `issues` can carry a `heavy_reread` warning.
- CI: the CHANGELOG gate now auto-exempts Dependabot dependency-bump PRs — they
  can't add a changelog bullet and the bump PR is itself the record — so
  dependency updates no longer show a spurious failing `changelog` check (on the
  PR or the merge commit).

## [0.4.23] — 2026-07-08

### Fixed
- **Trust-claim honesty sweep (2026-07-08 audit).** An adversarial sweep of every
  place the app renders a verification/trust claim found and fixed a cluster of
  copy defects that over- or mis-stated a rip's trustworthiness:
  - The User Guide's grey ("no tracks matched") verdict said the per-track Copy
    CRC "proves the disc was read securely" — an **overclaim**. A lone Copy CRC
    only shows the FLAC losslessly encodes what was read; it doesn't prove the
    read (or offset) was correct — a wrong-offset rip has a self-consistent Copy
    CRC. Reworded to match `verdict.py`'s honest wording.
  - Removed the stale **"experimental" CTDB caveats** that the KDD-16 hardware
    validation (`CRC_VALIDATED` → True) left behind in the Settings checkbox
    label + tooltip, the User Guide, the doctor/preflight hint, and the
    rip-progress comments/docstring — a CTDB match now legitimately reads as
    *verified*, so the copy no longer says it "never [says] verified".
  - The per-track EAC-CRC tooltip for a non-matching track said it "isn't in the
    AccurateRip database"; it also fires for a track that **is** present but
    whose CRC didn't match, so it now says "didn't match … either it isn't
    present, or the read didn't match a stored copy".
  - Softened two other over-broad claims: repeated re-reads "converge on a
    stable, repeatable read" (not "the bit-perfect result"), the read offset is
    "the one calibration a bit-perfect rip depends on" (not what "makes rips
    bit-perfect"), and the drive-setup cache line no longer calls a non-caching
    drive's reads "already trustworthy". Regression tests lock the honest copy.

### Security
- **Deterministic build timestamps (`SOURCE_DATE_EPOCH`) toward a reproducible
  AppImage.** `build_appimage.sh` now pins every timestamp the build embeds (the
  wheel's zip entries and the AppImage squashfs) to the HEAD commit time, so
  rebuilding the same commit yields byte-identical output — verified for the
  wheel (identical SHA-256 across runs). Combined with the build-provenance
  attestation, a third party can both verify *who* built a release and *rebuild
  it*. Full dependency byte-pinning (`pip --require-hashes`) remains a documented
  limitation: python-appimage's per-line shell `pip install` plus the unhashed
  locally-built wheel make it inexpressible in this recipe (details in
  `build/python-appimage/requirements.txt`).
- **Build-provenance attestation for the released AppImage (2026-07-08 trust-audit
  follow-up).** `release.yml` now runs `actions/attest-build-provenance` over the
  built AppImage, producing a signed SLSA provenance statement (GitHub OIDC +
  Sigstore — no maintainer-held key, no new runtime dependency) that binds the
  binary's SHA-256 to the workflow and commit that built it. Anyone can now prove
  a download really came from this repo's pipeline with
  `gh attestation verify platterpus-x86_64.AppImage --repo rmccann-hub/Platterpus`
  (the `.sha256` proves *integrity*; this proves *authenticity*). The in-app
  updater still checks only the SHA-256 for now; SECURITY.md documents that
  boundary. PyPI wheels are already attested via Trusted Publishing.
- **Supply-chain hardening round 2 (2026-07-08 trust-audit follow-ups).** All CI/
  release GitHub Actions are now pinned to full commit SHAs (with a `# vN` comment)
  instead of mutable tags, so a re-pointed tag can't inject code into the pipeline
  that builds the auto-updated binary; Dependabot keeps the pins current. Added a
  gating **`pip-audit`** CI job (dependency-vulnerability scan, currently clean),
  an advisory **`tests-touched`** check that warns when `src/` changes without a
  test, and a weekly non-blocking **mutation-testing** workflow (`mutmut` over the
  parsers, verdict, and CTDB CRC) for test-efficacy signal.

### Added
- **A known-disc re-rip no longer silently overwrites an existing rip.** Ripping
  an already-identified album to a folder that already holds audio now asks first
  — **Replace**, **Rip to a new folder** (lands in a fresh `… (2)`/`(3)` sibling,
  tags unchanged), or **Cancel** — instead of quietly clobbering the archival
  master. Completes the overwrite-safety work started for unknown discs in
  v0.4.22 (from the 2026-07-08 trust audit).
- **Static type-checking in CI (`mypy`).** The project mandates type hints but
  nothing verified them; a new gating `typecheck` CI job now runs `mypy` on every
  push/PR. It's a deliberately non-strict baseline over the whole package **except**
  the Qt UI mixin layer (excluded with a documented ratchet — it needs a shared
  Protocol/typed base first). Introducing it surfaced and fixed 17 real
  type-annotation gaps in the non-UI code (loose `object` types at loosely-coupled
  seams, an incorrect `CompletedProcess[str]` return, a Qt `setWindowIcon` on the
  wrong base class) — all fixed with proper annotations, no behaviour change.

### Documentation
- **Documented cyanrip's filename/path cross-filesystem behaviour** (naming-scheme
  audit, 2026-07-08). `docs/dependency-contracts.md` now spells out what cyanrip
  sanitises (`:`→`∶`, value `/`→`∕`) and what it does *not* (Windows/NTFS/exFAT
  reserved chars/names, trailing dots/spaces, case-insensitive collisions) — a
  documented cross-filesystem limitation that is harmless on the Linux target and
  never a silent bug (unwritable names fail the rip loudly). No behaviour change.
- Corrected stale "not on PyPI yet" install docs: the wheel has in fact been
  publishing to PyPI on every tagged release via Trusted Publishing, and
  `pipx install platterpus` is live (verified through v0.4.22). Updated README,
  PLANNING, TASKS, and test-plan Test 7 (marked done).

## [0.4.22] — 2026-07-08

### Fixed
- **An unknown disc can no longer silently overwrite a previous unknown disc's
  archival master.** Two unrecognized discs both default to
  `Unknown Artist/Unknown Album/…`, so the second rip used to clobber the first.
  An unknown-disc rip whose target folder already holds audio now lands in a
  fresh `… (2)`/`(3)` sibling instead (from the 2026-07-08 trust audit).
- **Durability of saved state.** Config, the drive-profile ledger, and the JSON
  rip report claimed crash- *and power-loss*-safe writes, but temp+rename without
  `fsync` is only safe against a process crash. A new shared `atomic_write`
  helper (temp → fsync → rename → parent-dir fsync) makes the claim true.
- **Config no longer loses a newer version's settings on a downgrade.** An older
  binary loading a config written by a newer one dropped the unknown keys on the
  next save; `config.save` now preserves them (and a higher `schema_version`).

### Security
- **CI hardening (2026-07-08 trust audit):** least-privilege `permissions:
  contents: read` on the CI workflow; a server-side `media-guard` job that
  rejects any push/PR introducing audio/copyrighted media (Critical Rule #8,
  previously only a client-side git hook); a `.github/dependabot.yml`
  (`pip` + `github-actions`) dependency watch; and a `SECURITY.md` disclosure
  policy. Deeper items (update signing, action SHA-pinning, reproducible builds,
  static type-checking) are tracked in `TASKS.md` and `docs/archive/trust-audit-2026-07-08.md`.

## [0.4.21] — 2026-07-08

### Fixed
- **The in-app User Guide (Help → User Guide) now shows the running version.**
  It carried no version at all — an oversight in the doc version-stamp pass,
  which only covered Markdown files while the guide lives in `help_content.py`.
  A footer now stamps `Platterpus vX.Y.Z (build …)` at render time, read live
  from `__version__` so it always matches the app you're running and can't go
  stale (same approach as the About dialog).

### Added
- **`scripts/file_versions.py`** — a git-derived "last updated (version)" report
  for *every* tracked file (`--markdown` for a committable manifest, `--path` to
  filter). Gives the whole-repo currency view for inspection without embedding
  stamps in source files (git is the source of truth there; a hand-typed stamp
  would rot). Docs keep their visible footer because they're read where git
  history isn't at hand; source does not.

## [0.4.20] — 2026-07-07

### Documentation
- **Every Markdown doc now carries a `*Last updated for Platterpus v0.6.12b6.*`
  footer** — the release its content was last revised for, so a reader can judge
  currency at a glance. Seeded from git history; bump it when you change a doc
  (documentation-currency convention, see `docs/README.md`).
- **Command-line usage of the AppImage.** Documented that the diagnostic flags
  (`--version`, `--doctor`, `--ctdb-calibrate`) work by passing them to the
  AppImage directly (there is no `platterpus` on `PATH` unless installed via
  `pipx`), plus a path tip for the U+2236 look-alike colon in rip-folder names.
  New README *Command-line usage* section + a `platterpus: command not found`
  troubleshooting entry.

### Changed
- **CTDB verify is now hardware-validated — a match reads "verified," not
  "experimental" (KDD-16).** A `platterpus --ctdb-calibrate` run on a real
  in-database disc (The Police — *Every Breath You Take: The Classics*, Pioneer
  BDR-209D) reproduced a stored CTDB CRC bit-exactly at aligned **offset 0**, so
  `ctdb/crc.py::CRC_VALIDATED` is now `True`. A CTDB `MATCH` is trustworthy (shown
  "verified" with confidence) and a `NO_MATCH` now legitimately means the rip
  differs from the database. The confirmed vector (whole-disc frames, front/back
  trim, offset, CRC) is recorded as `crc.CONFIRMED_VECTOR` and pinned by a
  regression test so the trim/offset math can't silently regress; the honesty
  behaviour for a future re-opened gate stays covered.

## [0.4.19] — 2026-07-07

### Fixed
- **CTDB calibration was ~150× too slow (`--ctdb-calibrate` and CI).** The offset
  sweep rebuilt the full GF(2) `crc32_combine` operator for every one of ~11,759
  offsets *and* for every prefix length, even though the window length is
  constant and the prefix lengths are arithmetic. Build each operator once and
  apply a cheap per-offset multiply: a full sweep dropped from ~40 s to ~0.3 s
  (bit-identical output, asserted against the naive per-offset CRC). This also
  removes a coverage-time CI stall the offset-range widening had introduced.
- **Read offset was silently wrong — the app's core promise.** A cluster of
  bugs in the read-offset chain (a wrong offset makes every rip NOT bit-perfect):
  - **cyanrip has no offset finder.** "Detect" ran `cyanrip -f` (which is
    *force-overread*, not an AccurateRip finder) and scraped a number from its
    output — latching onto a default/echo **0** and saving it as the offset, with
    a false **"measured on this drive (high confidence)"** label. Removed: cyanrip
    now honestly reports it can't auto-detect, and the offset comes from the
    bundled AccurateRip drive-model list (e.g. **+667** for the Pioneer BDR-209D)
    or manual entry. The "Detect" button is hidden when the backend can't measure.
  - **Agreement-based confidence.** An offset is **HIGH** confidence only when two
    independent sources agree (e.g. the AccurateRip list value and your entry);
    a lone reading is at most MEDIUM. A disagreeing automatic reading can no
    longer clobber a correct AccurateRip-list or manual value.
  - **whipper.conf no longer falsely satisfies the offset gate.** A leftover
    `whipper.conf` offset is never passed to cyanrip, so counting it as
    "configured" made an upgrader's rip run at offset 0; now only the GUI override
    (what cyanrip actually receives via `-s`) counts, so the AccurateRip-list
    auto-apply / setup wizard kicks in as intended.
  - **Self-heal + disagreement warning.** If the saved offset disagrees with the
    AccurateRip drive-list value for the selected drive, the rip preflight
    surfaces it and offers to use the list value (instead of silently ripping at
    the wrong offset), recording the accepted value so the trust line updates —
    but it never offers to overwrite a *deliberate* per-unit offset (a MANUAL
    entry or a two-source-CONFIRMED value), so a measured offset on one of two
    same-model drives is respected. The trust line also flags the disagreement.
- **AccurateRip verdict no longer over-claims.** When no track matched
  AccurateRip, the verdict said matches were "expected for a CD-R" and that the
  Copy CRCs "prove a secure read" — false reassurance on what may be a
  wrong-offset rip. It now honestly says the audio is *not independently
  verified* and names the possibilities (not in the DB / AccurateRip unreachable
  / wrong offset).
- **Dependency-install dialog crash (root cause of the CI flake).** The pending-
  installs dialog destroyed its install **worker** by dropping the last Python
  reference on the GUI thread while the worker's own thread was still alive — a
  wrong-thread QObject destruction that intermittently aborted the process
  (SIGSEGV/SIGABRT). The worker is now destroyed on its own thread via the queued
  `deleteLater`, and the Python references are cleared only after the thread's
  event loop has fully stopped. This is the real defect the CI test-retry
  wrapper was masking (local abort rate on the two worst test files dropped from
  ~40–55% to 0/25).

## [0.4.18] — 2026-07-07

### Added
- **Software-version provenance in the EAC-compatible log.** The companion
  `<name> (EAC-compatible).log` header now records **which softwares produced
  the rip** — *Platterpus &lt;version&gt; (build &lt;fingerprint&gt;)*, the
  **FLAC encoder** (flac + metaflac versions), and **ffmpeg** when a derived
  format (MP3/WavPack/WAV) was produced — alongside the cyanrip line it already
  carried. Values come from the launch-time dependency probe; an unmeasured
  version is omitted, never invented, and the "NOT a genuine EAC log / no EAC
  checksum" honesty guardrails are unchanged. (Previously the log named
  "Platterpus" with no version and omitted the encoder versions.)
- **Version in the window title.** The main window title now reads
  *"Platterpus &lt;version&gt;"* so the running version is visible at a glance,
  not only in Help → About.
- **EAC column in the results table.** The per-track AccurateRip results table
  gains an **EAC** column showing each track's EAC-format CRC32 (the value to
  compare against a real EAC rip) plus a ✓ when the track meets the archival bar
  Platterpus can verify (AccurateRip-verified + copy OK on an offset-corrected,
  error-free rip). Offset-variant-only matches show `~` (partial), and a track
  absent from AccurateRip shows the value with no mark — never a false ✓, and
  the tooltip is explicit it is *not* a claim of EAC-checksum equivalence.

### Fixed
- **CTDB offset search range corrected (KDD-16).** Calibration swept
  AccurateRip's ±2939-frame window; CTDB actually matches over
  **±(stride/2 − 1) = ±5879** (verified against the CueTools C# source). The
  CRC, trim, and offset-combine were already correct — a pressing whose
  alignment sat in (2939, 5879] was simply never reached, which is why two
  hardware calibrations returned no-match. Still gated by the fail-safe
  (`CRC_VALIDATED = False`, shown "experimental") until a hardware
  `--ctdb-calibrate` run confirms an offset-0 match.
- **`--doctor` / preflight now stamps the Platterpus version + build** in its
  header, so a pasted doctor report identifies the exact build.
- **Settings label rendered wrong.** "Also save back cover & booklet images"
  showed as "back cover  booklet images" (Qt ate the lone `&` as a mnemonic and
  bound a stray Alt+Space); reworded to "and".
- **CI test stability (internal).** The CI test step now retries **only** on a
  process-level abort (SIGABRT/SIGSEGV/SIGBUS, or a per-attempt `timeout` hang) —
  the known offscreen-Qt/PySide teardown/worker-thread race in the headless test
  harness that reddened the matrix at random. A real test failure or coverage
  miss (exit 1) is never retried, so the gate keeps all its teeth; each retry is
  logged as a CI warning, and a per-attempt timeout bounds the old 6-hour hang.
  No product code changed. (See `docs/testing.md`.)

## [0.4.17] — 2026-07-07

### Changed
- **CTDB CRC algorithm corrected (KDD-16).** The CUETools DB per-disc CRC was
  reconstructed bit-for-bit from the CueTools LGPL source: it *is* a plain zlib
  CRC-32 — the old code only got the **trim** wrong (it used no trim; the real one
  is a fixed 5880-frame front trim and a length-dependent back trim). CTDB verify
  now computes the correct value, and `platterpus --ctdb-calibrate` sweeps the
  ±2939-sample offset window (fast `crc32_combine`) to confirm it against a real
  in-database disc. Still shown as **experimental** until a hardware run flips the
  validation flag (fails safe until then). See `docs/ctdb-crc-algorithm.md`.

### Docs
- **Honest gap + strategy documentation.** Recorded that elite-tracker (RED/OPS/
  Orpheus) log acceptance is out of scope for the cyanrip backend by design
  (their logcheckers gate on ripper *identity*, plus a checksum we refuse to
  forge) and that cache-defeat is reported "attempted, not measured" rather than
  faked (PLANNING.md KDD-24/25). Added a per-gap, license-compatible open-source
  option menu (`docs/cyanrip-fork.md` Part A §10) and corrected stale
  whipper-era claims across the docs after the KDD-18 backend swap.

## [0.4.16] — 2026-07-06

A quality-of-life + reporting release: clearer progress, unattended-rip alerts,
richer metadata and cover art, and a more complete per-album report.

### Added
- **The rip status line now shows "track N of M".** During a rip the label reads
  *"Ripping track 12 of 17… 42%"* instead of just *"Ripping track 12…"*, so you
  can see how far through the disc you are at a glance. The total comes from the
  MusicBrainz metadata (correct from the first progress line) and falls back to
  cyanrip's disc banner; when the count is genuinely unknown the "of M" is
  omitted rather than shown wrong.
- **Live per-track status in the track list.** A new *Status* column marks each
  track *⟳ Ripping* as the drive reaches it and *✓ Done* as it completes, so you
  can see at a glance which tracks are finished and which are still to come —
  alongside the existing current-row highlight. Clears back to blank at the start
  of each rip.
- **Desktop notification when a rip finishes.** An unattended rip now pops a
  desktop notification on completion (or failure) — e.g. *"Platterpus — rip
  complete · All 14 tracks verified against AccurateRip."* — so you don't have to
  watch the window. On by default (Settings → *After rip*); a rip you cancel
  yourself is not announced. It's a Qt system-tray message (no extra tool to
  install) and fails safe on desktops without notification support.
- **Back cover and booklet scans are now saved too.** When cover art is enabled,
  Platterpus also fetches any back cover and booklet images the Cover Art Archive
  has for the release and saves them beside the audio (`back.jpg`,
  `booklet-NN.jpg`) — the front cover is still embedded as before. On by default
  (Settings → *Cover art → Also save back cover & booklet images*); these can't be
  embedded in FLAC, so they're saved as files.
- **Set cover art from a local file.** *Tools → Set cover art from file…* lets you
  pick your own image (a good scan, a corrected cover) to use as the front cover
  for the disc on screen, instead of the archive fetch — embedded/saved on the
  next rip. The file is checked to be a real image when you pick it.
- **UPC/barcode, catalog number, and label are now captured and tagged.** When
  MusicBrainz has them, the release's barcode (UPC/EAN), label catalog number, and
  record label are written to the audio as standard `BARCODE`/`CATALOGNUMBER`/
  `LABEL` tags and recorded in the JSON rip report, so the library entry carries
  the disc's canonical identifiers.
- **Optional EAC-compatible log beside each rip.** A new Settings toggle
  (*EAC-style log*, off by default) writes an honest, clearly-attributed
  EAC-*layout* text log — *"… (EAC-compatible).log"* — next to the audio after a
  successful rip, so you can diff it against a real EAC log or keep a familiar
  record. It is plainly marked as generated by Platterpus and is **never** a
  signed/forged EAC log.

### Changed
- **The JSON rip report now records the full cover-art package.** Beyond the front
  cover, the report's `cover_art` block lists any back/booklet images saved
  (`additional_saved`), and the `disc` block carries the release's catalog number,
  barcode, and label — so the one-file per-album record reflects everything the rip
  produced.

### Fixed
- **The disc view now clears when you eject or remove the disc.** Previously the
  disc-ID/MusicBrainz panel and the track list kept showing the *previous* disc
  after it left the drive, so the app looked like it still had that disc loaded.
  The media watcher now detects the disc→empty transition (an eject or a physical
  removal) and blanks the "what's in the drive now" view within a couple of
  seconds — while the last rip's results pane stays put so you don't lose your
  outcome.

## [0.4.15] — 2026-07-06

### Fixed
- **Offset-variant tracks no longer read as "bad rip" in the results table.** A
  track that matched the database only at the common +450-frame pressing offset
  (a *partially-accurate* match — perfectly good archival audio) used to show
  cyanrip's raw *"not found, either a new pressing, or bad rip"* in the AR v1/v2
  columns, which looked alarming even though the banner said the track was fine.
  Those cells now read **"offset-variant match (N)"**, surfacing the partial
  match the report already recorded. Genuinely not-in-database tracks now read a
  plain **"not in DB"** instead of the *"…or bad rip"* phrasing (a track absent
  from the database isn't necessarily a bad rip). Same trust-first principle as
  the CTDB honesty fix; surfaced by the real-hardware Roots compilation, whose
  tracks 11–17 are legitimate offset-variant matches.

## [0.4.14] — 2026-07-05

### Changed
- **The time-remaining estimate is now duration-weighted, so it stops
  oscillating.** The progress bar used to give every track an equal slice
  regardless of length, so a long track made the bar (and the ETA) crawl while a
  short one made it race — the estimate swung by ~10 minutes across a disc. Each
  track's slice is now sized by its real MusicBrainz duration, so the bar tracks
  *audio position* — and, at a steady read speed, wall-clock — making the ETA
  much steadier and more accurate. Falls back to the old equal-slice behaviour
  when track durations aren't known (an unknown disc, or partial metadata), so
  nothing regresses there.

## [0.4.13] — 2026-07-05

### Added
- **The time-remaining estimate now says when the drive is *stalled*.** A
  scratched or smudged spot can make a drive retry the same audio for a very long
  time (real hardware: a single track that hung for hours). The estimate used to
  keep showing a normal — and eventually absurd — countdown through that. Now,
  when the disc makes no meaningful forward progress for a few minutes, the status
  line reads *“stalled 4m — the drive is stuck on a hard-to-read spot (a scratch
  or smudge)”* instead of a misleading “time left”. A merely-slow-but-advancing
  read is never mislabelled, and the countdown returns on its own once the drive
  gets past the spot. **The stall is also recorded** — a warning is written when
  it starts and an info line when it recovers — so it lands in both `log.txt` and
  the rip report’s embedded debug log, not just the transient status line.
- **Every `log.txt` file now carries a Platterpus version banner.** A line like
  `──── Platterpus 0.4.13 (build abc1234) ────` is stamped at the top of the log
  at each session start *and* on every rotation, so a log excerpt in a bug report
  — even a rotated backup — always says which build wrote it. (The JSON report
  already records the version and build fingerprint in its `generator` block.)
- **`platterpus --version` and Help → About now show the build fingerprint** — the
  exact git short-SHA of a built AppImage (or `source` for a checkout) beside the
  version number — and it’s written to the log at startup. A bug report now
  carries the precise build, not just the marketing version. (It was already in
  the JSON rip report; this surfaces it in the two other places a user reads a
  version.)

### Changed
- **The `.platterpus.json` rip report is now always fully verbose.** Its embedded
  session log (the `debug` block) previously captured only INFO-level detail
  unless you had first turned on “Debug logging” in Settings — so a report sent
  for a problem rip was often missing the subprocess/probe/parse steps needed to
  diagnose it. The report’s in-memory log buffer is now held at DEBUG *always* (it
  lives only in memory and is bounded, so this is free), making every report a
  complete, debuggable record out of the box. The “Debug logging” setting now
  governs only how verbose the on-disk `log.txt` is.

### Fixed
- **The rip status no longer says “Encoding” for the whole rip.** cyanrip reads
  *and* encodes each track in one pass (“Ripping and encoding track N”), and
  Platterpus labelled that “Encoding track N…” — so during a normal ~1× secure
  rip the status showed “Encoding track 1… 7%” crawling for minutes, which read
  as if encoding (which is near-instant) was the slow part instead of the disc
  read. Both cyanrip progress forms are now labelled **“Ripping track N…”** —
  one honest verb that matches what’s happening (and stops the label flickering
  between “Reading”/“Encoding”). Surfaced by the real-hardware Police rip.
- **A cancelled rip no longer logs a scary traceback when writing its report.**
  If a rip is cancelled and its album folder is removed, the best-effort report
  write found the folder gone and logged a full `FileNotFoundError` traceback at
  `WARNING`, which reads like a crash. That benign case is now a concise `INFO`
  line (“skipped rip report; album folder no longer exists”); a genuine write
  error still logs the full detail. Surfaced by the real-hardware Roots cancel.

## [0.4.12] — 2026-07-05

### Added
- **The `.platterpus.json` rip report now builds incrementally.** As each track
  finishes, a partial report (`outcome.status: "in_progress"`) is written beside
  the growing cyanrip `.log`, off the GUI thread and atomically. So a hard stop
  that never reaches the normal finish handler — a power loss, a `SIGKILL`, an OS
  crash — still leaves a report of the tracks completed so far, not nothing. (A
  normal finish or cancel still writes the full report, superseding the
  partials.) The human `.log` and the app `log.txt` were already incremental;
  this closes the gap for the JSON.
- **A freshly-inserted disc is detected automatically.** After cancelling a rip
  (which force-stops *and ejects* the drive), putting a new CD in did nothing
  until a manual “Rescan disc”. Platterpus now polls the drive's media state
  (a lightweight `CDROM_DRIVE_STATUS` check that never spins the disc) while
  idle, and auto-runs the same rescan the moment a disc appears — so a new disc
  is picked up on its own. Skipped entirely while a rip or scan holds the drive;
  best-effort (degrades to the old manual-Rescan behaviour if the drive can't be
  queried).

### Changed
- **The rip status line now carries a timestamp** (`HH:MM:SS · …`), so a glance
  — or a screenshot — shows *when* the current phase was reached.

## [0.4.11] — 2026-07-05

### Fixed
- **CTDB "no match" no longer implies your rip is bad.** The results panel used
  to say *"CTDB: no match — this rip differs from the database entries"* on every
  rip — even a rip AccurateRip had just verified at confidence 200. That was a
  false alarm: the CTDB CRC algorithm is still a placeholder pending hardware
  validation (KDD-16), so its CRC is *expected* to disagree and a non-match says
  nothing about the rip. The verdict now branches on whether the CRC algorithm
  is hardware-validated — until it is, a no-match reads as *"not confirmed — the
  CRC check is still experimental; a non-match here doesn't mean your rip is
  wrong."* AccurateRip remains the authority. (Same guard on the `.log`/report
  wording.) Surfaced by the real-hardware v0.4.10 rip of The Police.

### Added
- **The rip report's `ctdb` block is now self-diagnosing** (report schema v8).
  It records the database's expected CRC(s) (`db_crcs`) and `entry_count`
  alongside our computed `our_crc`, so a no-match can be diagnosed — and the
  CTDB-CRC algorithm calibrated — straight from a saved report, without a second
  live lookup.
- **`platterpus --ctdb-calibrate <folder>`** — run a CTDB verify + CRC-offset
  calibration over an already-ripped album folder (no CD, no re-rip) straight
  from the AppImage. It prints the disc TOC, the lookup URL, the verdict, and —
  if the disc is in CTDB — sweeps the candidate offset-guard trims and reports
  which one reproduces the database CRC. That discovered trim is the
  hardware-validated CTDB-CRC algorithm (KDD-16). The standalone
  `scripts/ctdb_verify.py --calibrate` now shares the same engine.

## [0.4.10] — 2026-07-03

### Fixed
- **The setup wizard no longer freezes the window while it checks what got
  installed.** After the host-setup wizard ran, Platterpus re-probed each
  container tool (cyanrip/flac/metaflac) on the GUI thread — and each probe
  shells into the Distrobox container, which can take up to minutes on a cold
  container, so the window locked up. The re-probe now runs on a worker thread
  while a nested event loop keeps the window responsive.
- **A batch of small robustness + hardening fixes.** The in-app updater now caps
  the `.sha256` read (a hostile mirror could otherwise stream a huge body into
  memory before the length check); the CTDB verify now classifies a wedged
  `flac`/`metaflac` (`TimeoutExpired`) as a lookup/decode error instead of
  letting it escape the never-raise path; the metaflac tool-path Settings field
  now rejects control characters (the other path fields already did); Picard is
  launched detached (`start_new_session`) so quitting Platterpus can't take it
  down; the dialog-centering filter tracks dialogs by weak reference instead of
  `id()` (a reused id could leave a later dialog un-centred); and the AppImage
  `.desktop` `Exec=` writer neutralises newline/tab/CR so a control character in
  the path can't inject a second key. Each carries a regression test.
- **A rip that finishes could no longer leave the app wedged.** Three latent
  failures in the finish path are closed: (1) the post-rip tagging step read the
  track-table widgets from its background thread — a data race on every
  unknown-album rip; the table is now snapshotted on the GUI thread and the plain
  data handed in. (2) A `.log` vanishing mid-scan while discovering the rip log
  raised an error that escaped the worker, so `finished` never fired and the rip
  lock stuck on (drive spinning, UI dead until restart); log discovery now stats
  each candidate once, guarded, and `start_rip` always emits `finished` even on
  an unexpected error. (3) If anything in the finish handler raised, the rip-state
  clear was skipped, so shutdown thought a finished rip was still live; the reset
  now runs in a `finally`. Each has a regression test.
- **The album ETA is no longer wildly optimistic early in a rip.** It projected
  the remaining time from the average rate *since the pass began*, but the disc
  scan (first ~5%) and the disc's inner tracks read far faster than the bulk — so
  early on the estimate was dominated by that fast start and read absurdly low
  (real hardware: at 5% done it showed "~4m left" with 58m to go, then climbed).
  It now projects from the read rate over a trailing 90-second window, so it
  tracks the actual current speed and stays honest throughout instead of starting
  low and ramping up.
- **Upgraders no longer inherit the dynamic secure re-rip switched *off*.** The
  0.4.9 headline (secure only the AccurateRip-failing tracks) needs the "Max reads
  to confirm a shaky track" ceiling (`-Z`) above 0, and a fresh install defaults
  to 2 — but anyone upgrading from 0.4.8 (whose default was 0) kept the old 0, so
  the feature silently never ran (confirmed on real hardware: a rip with
  `secure_rerip_matches: 0` and no `-Z`). A one-time config migration (v6→v7) now
  bumps an inherited `0` to `2` so the feature actually engages. It runs once, so
  anyone who genuinely wants re-rip off can set `0` again afterward and it sticks.
- **A literal `%%` in a naming template now produces one `%` in the filename, not
  two — and matches the live preview.** The template-to-cyanrip translator didn't
  recognise `%%` (whipper's escape for a literal percent): it passed `%%` through
  unchanged, so the real filename had two percent signs while the Settings preview
  showed one, and every rip using such a template logged a bogus "no cyanrip
  mapping for token '%%'" warning. Now `%%` collapses to a single `%` (as the
  preview always did), so preview and result agree and the spurious warning is
  gone. (Found while re-checking a deferred audit note that turned out to be a
  real preview-vs-result mismatch, not the "intentional" behaviour it was filed
  as.)
- **Settings validation now rejects a control character at the *start or end* of
  an output/working directory, not only in the middle.** The check ran on the
  whitespace-stripped value, and Python treats the C0 "information separators"
  `\x1c`–`\x1f` (and tab/newline/CR) as whitespace — so a leading or trailing one
  was trimmed away before the check and slipped through, yet stayed in the saved
  config and reached the rip as a real path character. Now checked on the raw
  value, so the "no control characters in a path" rule holds at every position
  (NUL was always caught; this closes the gap for its whitespace-classified
  siblings). Found by a new position-fuzzing property test.

### Changed
- **In-app help and the README now describe how ripping actually works.** The
  re-rip control is named "Max reads to confirm a shaky track" (not the old
  "Re-rip until reads match"), and the help/README explain the dynamic model —
  rip once fast, then secure-re-rip only the tracks AccurateRip couldn't confirm
  — which is **on by default** (they used to say "leave it Off for clean discs").
  A "How ripping works" section was added to the README.
- **Documentation currency (KDD-18 follow-through):** swept remaining
  whipper-as-the-current-backend claims out of the docs, the drive-setup wizard
  wording ("saves to whipper.conf" was false — the offset lives in Platterpus's
  own config, applied to cyanrip), and code comments, while keeping the
  legitimate references (the whipper-format log parser, the legacy `whipper.conf`
  offset reader, and clearly-labelled inert seams). Removed the dead
  `scripts/preflight.py --backend whipper|cyanrip` flag (it set a `Config`
  attribute that no longer exists), the dead `DriveSetupResult.backup_path`
  field, and corrected the Python matrix (3.11–3.14) and a few table/reference
  nits.
- **After an in-app update, the "Restart now?" prompt now warns that the new
  version can take 20–30 seconds to reappear** (a new AppImage unpacks itself on
  its first launch). The app *does* relaunch itself, but that cold-extract gap
  read as "it updated but didn't restart" (real-user report, 2026-07-02) and led
  to reopening it by hand. Setting the expectation up front fixes the confusion
  without changing the (correct) relaunch behaviour. Regression-tested so the
  heads-up can't be silently dropped.

### Added
- **"View log" and "View report" now open in an in-app read-only viewer.** A
  `.log` / `.platterpus.json` has no default application on a fresh KDE, so the
  old behaviour popped the OS "Open With" app-chooser (a jarring, un-asked-for
  prompt against the zero-terminal bar — real-user report). The files now show in
  a self-contained, read-only, monospace pane; an "Open externally…" button still
  hands off to your own editor when you want it. ("Open rip folder" still uses
  the file manager, which does have a default handler.)
- **The rip report (`.platterpus.json`) now explains a whole rip on its own
  (schema v7).** New, additive sections so one file answers the questions a
  support thread always asks: `outcome` (did the *run* succeed / cancel / fail,
  with a failure hint and whether the "re-rip as unknown" self-heal fired —
  distinct from the AccurateRip `verdict`); `settings` (what the GUI *asked the
  ripper for*, including the read offset as `{configured, applied, effective}` so
  a genuine 0 is told apart from a configured-but-not-applied one — which the log
  can't show); `disc` (unknown-mode + the MusicBrainz release id); `environment`
  (Python / OS / PySide6 / install channel, plus per-dependency versions **and
  paths** from the launch-time probe — cyanrip/flac/metaflac/ffmpeg/…); a
  `generator.build_fingerprint` (the build's git short-SHA, or `"source"` on a
  checkout — debug only, never part of any bit-perfection claim); `cover_art`
  (the structured front-cover result — found / why-not, e.g. `404` vs `network`,
  and how many files it was embedded in); `read_speed.secure_rerip` (why the
  dynamic secure re-rip did or didn't run — e.g. skipped because the disc isn't
  in AccurateRip, so "why wasn't my shaky track re-ripped?" is answerable);
  `verification.gates` (turns an ambiguous `null` check into an explicit "ran" /
  "disabled" / "backend self-verifies" / "flac-only"); `verification.recompress`
  (the opt-in `flac -8` result, which mutates the masters); `log_parse` (flags a
  degraded read of the human log); and a consolidated, severity-tagged `issues`
  list a triager opens first (empty on a clean rip). A hard failure that produced
  **no** log now also leaves a minimal report
  (`platterpus-rip-failure.platterpus.json`) so the most-broken rips are no
  longer the least diagnosable.
- **A report-completeness test now fails CI if a report section goes missing or
  a new one is added without being declared** (`test_rip_report_completeness.py`)
  — the JSON's whole value is that a consumer can rely on every section being
  present-or-explicitly-null, so a check can't be added to the rip and silently
  left out of the report.
- **Property-based (fuzzed) tests for two never-raise/security surfaces:** the
  naming live-preview renderer (`render_preview` must never raise on any typed
  template) and the Settings path validators (a `..` traversal segment, and a
  control character, must be rejected wherever they appear — not just in the few
  hand-picked example positions). These complement the existing example tests and
  guard against a refactor accidentally narrowing a check's scope.
- **Fault-injection tests for the host step-engine's real subprocess runner**
  (`SubprocessRunner`): a missing command surfaces as the `127` sentinel and a
  timeout as `124` — never an exception that would abort the setup/uninstall
  pipeline mid-step. (Previously only the injected fake runner was exercised.)

## [0.4.9] — 2026-07-02

### Added
- **Dynamic secure re-rip is now how ripping works — no checkbox.** Platterpus
  rips the disc once at **full speed** (no `-Z`), then secure-re-rips **only the
  tracks that didn't match AccurateRip** (a track that matched the database on its
  first read is already proven bit-perfect, so re-reading it is wasted time). This
  used to be an opt-in checkbox; it's now the default behaviour with no toggle —
  the dialog clutter is gone (a power user can still force `-Z` on every track by
  hand-editing `secure_rerip_dynamic = false` in `config.toml`). It's **on by
  default** — a fresh install ships with the re-read ceiling (`-Z`) at 2, so the
  secure re-rip actually runs (at 0 the whole feature would be inert). On a clean
  disc that's a single fast pass (roughly real-time, no ballooning ETA); a disc
  in AccurateRip whose few tracks didn't match gets those secured, while a disc
  that isn't in AccurateRip at all keeps its fast read (there's no database
  consensus to verify against, so a re-rip couldn't prove anything). The re-rip
  reason (`instability` vs `accuraterip`) is recorded per track in the report's
  `read_speed.retried_tracks`.
- **The number you set is a *ceiling*, not a tax.** The "Max reads to confirm a
  shaky track" setting (cyanrip's `-Z`) is now the *most* effort spent on an
  unverified track, not a fixed cost applied to every track — relabelled to say
  so. There's no hardcoded ceiling beyond the settings spinner's own range (0–10),
  so your number is the max.
- **Input validation on every setting, with a visible error as you type.** A new
  pure `settings_validation` module checks every Settings value for type, range,
  character set, and format — output/working directories (absolute, writable-or-
  creatable), naming templates (relative, known `%`-tokens, renders to a real
  name), the metaflac path, and every number/choice/toggle. A red banner names
  what's wrong and marks the offending field *as you edit*, **OK is blocked** until
  errors are fixed, and every rejection is written to the log file. Exploit-shaped
  inputs are rejected outright — path traversal (`..`), control characters/NUL,
  and absolute templates that would escape the output folder.
- **Richer diagnostics in the `.platterpus.json` report (schema v6).** The `rip`
  block now records `speed_changeable` (whether the drive can change read speed —
  the field behind the `-S`-abort fix), and each track carries the extraction
  metrics cyanrip logs (`extraction_speed`, `extraction_quality`, `pre_emphasis`,
  `peak_level`) — so a re-rip's report reflects everything the log reveals.
- **New `docs/dependency-contracts.md`** — the single reference for the exact
  arguments, syntax, and expected output for every external tool Platterpus drives
  (cyanrip, flac, metaflac, ffmpeg, musicbrainzngs, Cover Art Archive, CTDB, and
  drive/reader control), so output-side validation has a documented contract.

### Fixed
- **Closing the app during a rip now stops the drive.** Quitting (or closing the
  window) while a rip ran left the optical drive spinning — the next track kept
  ripping until the disc was ejected by hand (real-user report). `cancel()` only
  killed the *host-side* wrapper; on rootless podman the in-container reader
  (cyanrip) is a separate process tree that podman doesn't forward the signal
  into. Closing now stops that in-container reader **synchronously** on the way
  out (the "exit = force stop" contract, done right) — no eject, just stop.
- **A failed transcode now logs *why*.** ffmpeg's stderr was being discarded, so a
  transcode failure left no diagnosis in the log. Its error output is now captured
  and the tail logged on any non-zero exit (the master FLAC is still never at
  risk — a per-file failure leaves the source untouched).
- **Closing a setup/uninstall dialog (or the app) during a long step no longer
  freezes or crashes.** The wizard, uninstaller, and drive-setup dialogs joined
  their worker thread on the GUI thread with waits up to two minutes — closing
  mid-`dnf`/mid-teardown hung the window (real-user report), and if the wait
  timed out the still-running thread was destroyed, aborting the app. All
  worker-thread teardown (those dialogs and the main window's close) now goes
  through one helper that cancels, waits briefly, and *detaches* a thread still
  stuck in an uninterruptible step (it finishes and cleans itself up) instead of
  blocking or destroying it.
- **A rip that isn't in the AccurateRip database no longer triggers a needless
  full second pass.** Dynamic secure re-rip is meant to re-read only the few
  tracks that didn't match AccurateRip — but a disc with no database entry at all
  (a CD-R, an obscure pressing) made *every* track "fail", so it re-ripped and
  replaced the whole disc for no benefit (there's no database consensus to match
  against). Such a disc now keeps its fast first read, flagged as not-verified.
- **A bad byte in a rip log can't derail the finish.** If a rip log contained a
  stray non-UTF-8 byte, reading it raised an error that aborted the entire
  post-rip step (no report, no tags, no cover art, no eject) and left the app
  thinking a rip was still running. The log is now read leniently and any
  rendering error is contained, so the rip always finishes cleanly.
- **The time-remaining estimate no longer balloons on a second pass.** The
  progress bar resets to 0% at the start of each rip pass (a read-speed retry or
  a secure re-rip), but the ETA still divided the *whole rip's* elapsed time by
  that fresh 0-based fraction — projecting a wildly inflated "time left" (e.g.
  hours) the moment a second pass began. The ETA now measures from each pass's
  own start, so it stays sensible across passes.
- **The album log stays honest after an auto-fix swap.** When a re-ripped track
  replaced the original, the whole-disc `.log` still recorded the *discarded*
  bytes' CRC — so the committed durable-proof text no longer matched the audio on
  disk. A clearly-delimited addendum is now appended to that log naming each
  swapped track and the shipped file's CRC (the original content is preserved
  verbatim; the `.platterpus.json` report already tracked the swap structurally).
- **A failed rip can't adopt a previous album's log.** The rip log is located by
  searching the output folder — which is the shared music root — for the most
  recent `.log`. A rip that failed before writing its own log would pick up a
  *previous* album's log from a sibling folder and parse it as this rip's. Log
  discovery is now scoped to logs written at or after this rip started, so an
  older album's log is ignored.
- **The auto-fix track swap can't corrupt a master.** When a re-ripped track
  replaced the original, it was copied straight over the file; a crash or full
  disk mid-copy could truncate a good archival FLAC. The swap is now atomic
  (write a temp, then rename), so the original is only ever replaced whole.
- **A rip-stream error no longer leaves the ripper running.** If reading the
  ripper's output failed mid-rip, the subprocess kept running and holding the
  drive; it's now stopped before the error is reported.
- **A later identified disc no longer rips as "Unknown".** Once a disc that
  couldn't be identified put the app in unknown-album mode, that mode stuck for
  the session — so the *next* disc, even a fully-identified one, could rip with
  the MusicBrainz release dropped and generic "Track N" filenames. Starting a
  new disc scan now clears it.
- **Rescanning a disc no longer stutters or risks a crash.** Starting a new scan
  while one was still running blocked the window for up to two seconds and could
  let a stale result from the old scan overwrite the new one. The old scan is now
  detached cleanly and its late result ignored.
- **Unknown-distro setup no longer silently fails on privilege escalation.** On
  a distro without a known package manager, the setup wizard fell back to the
  upstream Distrobox installer piped to a hardcoded `sudo sh` — but the GUI has no
  terminal for `sudo` to prompt on, so it failed silently. It now uses the same
  graphical elevation (`pkexec`) the wizard uses everywhere else.
- **A native cyanrip install no longer triggers the setup nag.** The first-run
  "set up Platterpus" check only looked for the container-exported cyanrip
  wrapper, so a user who installed cyanrip natively (on `PATH`) was still prompted
  to run host setup. The check now uses the dependency subsystem's host-presence
  test, which also counts a PATH-native cyanrip.
- **Uninstall now removes the exported `flac` wrapper too.** Setup exports
  cyanrip, metaflac *and* flac to `~/.local/bin/`, but both the in-app uninstaller
  and `uninstall.sh` removed only whipper/metaflac/cyanrip — leaving
  `~/.local/bin/flac` orphaned. It's now removed alongside the others.
- **CTDB verification uses far less memory.** It decoded every track and
  concatenated the whole disc's PCM (~750 MB) plus a join copy (~1.5 GB peak) on
  the verify thread before computing the CRC. It now folds each track into the
  running CRC one at a time, so peak memory is a single track — no behaviour
  change (the CRC is identical), just a large memory saving on modest machines.
- **The EAC-style exported log no longer invents a read mode.** The optional
  EAC-layout log hardcoded `Read mode: Secure` and `Make use of C2 pointers: No`
  regardless of the actual rip — but nothing in the parsed data backs those, so
  they were fabricated. Those two lines are now omitted (only fields actually
  parsed are rendered), keeping the export honest per its own "not a genuine EAC
  log" banner.
- **Force-stopping one drive no longer risks killing a rip on another.**
  Force-stop began with a name-matched `pkill cyanrip` (and cdparanoia/cdrdao),
  which would SIGKILL *any* such process on the system — including one ripping a
  different disc on a second drive. It now tries the device-scoped `fuser -k
  <device>` first (which targets only the process holding *that* drive) and falls
  back to the broad by-name kill only when there's no device to scope to or
  nothing held it.
- **Post-rip verification only looks at this album's files.** The CTDB, FLAC-
  integrity, and derived-file checks enumerated FLACs *recursively* under the
  album folder, so a FLAC in a nested subfolder (a bonus disc, a leftover — or
  the entire music library if the folder ever fell back to the output root) got
  pulled into the CTDB TOC (corrupting the CRC → a spurious "not in database") or
  inflated the transcode-completeness count. They now enumerate only the album
  folder's direct files, matching how the rip is actually laid out.
- **Checksums are never taken of a still-being-written file.** The per-file
  SHA256 step waits for post-rip tagging/transcoding to settle, then hashes — but
  if that work didn't finish within the settle window it hashed anyway, recording
  a digest of a mid-rewrite file as "integrity truth". It now checks whether the
  work actually settled and, if not, records no checksums (an honest omission)
  rather than a wrong one; the fidelity verdict is unaffected.
- **Start is locked while a disc is being scanned.** The disc probe holds the
  drive, but Start could still be pressed during a scan (in unknown-album mode a
  drive alone enables it) — starting a rip then contended with the probe for the
  device and let the scan's completion pop a dialog over an already-rip-locked
  window. Start is now disabled for the duration of a scan (with a tooltip saying
  why) and re-enables when it finishes.
- **A slow MusicBrainz lookup can't tag the *next* disc with the previous
  disc's album.** MusicBrainz lookups run in the background; if you swapped discs
  before a lookup finished, the late result (release candidates or the fetched
  release detail) could repopulate the new disc's tracks and release-id — tagging
  the new disc with the *previous* disc's metadata. Every lookup now carries the
  disc-id it was fired for, and a result whose disc-id no longer matches the disc
  on screen is dropped (the same staleness guard the disc probe already had).
- **A previous album's verification can't land in the next album's report.** The
  post-rip checks (CTDB, FLAC-integrity, transcode, per-file checksums, derived-
  file verify) run in the background and can outlast the rip; if you started a
  second rip before the first's checks finished, a late result could be written
  into the wrong album's report (and one result — the derived-file verify — was
  never even reset between rips). Each check now records which rip it belongs to
  and is discarded if a newer rip has started.
- **A hand-edited or corrupt config can't crash startup or slip a bad value into
  a rip.** A broken `config.toml` (invalid TOML, a non-numeric schema version)
  used to crash the app before it could even show an error; it's now backed up
  to `config.toml.bad` and the app starts from defaults. And because editing the
  file by hand bypasses the Settings dialog's checks, every loaded value is now
  validated the same way — any field with an error (e.g. a `..` path-traversal
  template) is reset to its default before it can reach the ripper, with the
  problem written to the log.
- **Failures in the FLAC verify / re-compress / derived-file checks are now
  logged.** These steps discarded the tool's error output, so a failed
  `flac --test` (corruption) or ffmpeg decode left no reason in the log. Their
  stderr tail (or exit code) is now captured on failure, matching the transcode
  step — so a bug report's log actually explains what went wrong.
- **A colon in the year, genre, ISRC, or release id is now restored in tags.**
  cyanrip can't take a literal `:` in a tag argument, so Platterpus feeds it a
  visually-identical lookalike and restores the real colon afterward. The check
  that decided whether to run that restore only looked at album/track title and
  artist, so a `:` in the year, genre, an ISRC, or the MusicBrainz release id was
  left as the lookalike in the written tag. It now checks every field fed to
  cyanrip.
- **The menu-entry launcher escapes special characters in its path.** The
  `.desktop` `Exec=` line dropped the AppImage path raw between quotes, so an
  AppImage under a folder containing `"`, `` ` ``, `$`, or `\` (e.g. a path with a
  dollar sign) could break the entry — or, in a launcher that hands the line to a
  shell, allow command substitution. The path is now escaped per the freedesktop
  spec for both the main and the uninstaller entries.
- **A stalled derived-file verify can't hang forever.** The post-transcode
  decode-verify bounded only the *wait after* ffmpeg finished; if ffmpeg stalled
  mid-decode holding the output pipe open, the read loop could block indefinitely.
  A watchdog now kills a decode that exceeds the deadline (which unblocks the read
  and reports the file as unverifiable) so the verify thread always makes progress.
- **The in-app updater caps the download size.** The AppImage download is now
  bounded (rejected up front if the server declares an oversized `Content-Length`,
  and aborted if the running byte count exceeds the cap) so a misbehaving or
  hostile server can't stream an endless body onto the disk before the existing
  post-download SHA-256 gate rejects it.
- **Hardening for the network lookups.** The CUETools-DB (CTDB) verification
  reads over plain HTTP, so its response is now size-capped — a misbehaving or
  hostile server can't return a giant body and exhaust memory. And the cover-art
  release id is URL-encoded into the request, so a tampered id can't rewrite
  which resource is fetched.
- **The window no longer freezes while identifying a disc.** MusicBrainz lookups
  were running on the GUI thread — the worker was moved to its own thread, but its
  slots were being *called* directly, which runs them on the caller's thread
  regardless. A slow or unreachable MusicBrainz would hang the whole window on the
  most common action (inserting an identified disc). Queries now genuinely run on
  the worker thread, and the MusicBrainz adapter bounds every request with a
  timeout so a stalled server can't hang the lookup at all.
- **Cancel no longer freezes the window.** Pressing Cancel during a rip forwarded
  to a blocking SIGTERM-then-wait on the GUI thread — a drive stuck in a kernel
  read could freeze the window for seconds. Cancel now sends a non-blocking stop
  signal and returns immediately; the reap and the force-stop escalation happen off
  the GUI thread as before.
- **Checking dependencies and refreshing drives no longer freeze the window.**
  Tools → Check dependencies, the Settings “Check dependencies” button, and the
  drive-picker Refresh button all probed the system synchronously on the GUI
  thread — each shells into the Distrobox container, which is slow on a cold
  start and could hang the window for tens of seconds. They now run the probe on
  a worker thread (the same off-thread path the launch check already used) and
  apply the result on the GUI thread.
- **The update dialog's Cancel button works again.** It was wired to the download
  worker's slot as a queued call, but the worker was busy downloading and never
  processed it, so Cancel did nothing and the update installed anyway. Cancel now
  flips the worker's flag directly from the GUI thread, and the download stops
  between chunks.
- **Dialogs open on the right screen, on top, and fully visible.** Every dialog is
  centred on the main window (a `CenteredDialog` base + an app-wide filter that
  also catches `QMessageBox`/`QFileDialog`), but two gaps remained on a
  multi-monitor desktop (real-user report — the "move to ~/Applications" prompt
  opened on the *other* monitor and *behind* other windows): (1) the centring
  never clamped to the visible screen, so a dialog centred on a window near an
  edge — or at a global coordinate XWayland reports oddly when monitors are
  fractionally scaled — could land partly or fully off-screen; and (2) it never
  raised the dialog, so a correctly-parented prompt could sit behind other windows
  until the user clicked the main window. Centring now **clamps** the dialog fully
  onto whichever screen the centred position lands on (pulling it back if that
  point is off *all* screens) and **raises + focuses** it so it comes to the
  front. No resize — just a slide; an oversized dialog pins its top-left so the
  title bar and buttons stay reachable.
- **The release workflow can't ship a mislabeled or invisible release.** Two
  release-side gaps are closed: (1) the built AppImage's `--version` is now
  asserted to match the release tag, so a forgotten `__version__` bump fails the
  build loudly instead of shipping a binary whose version disagrees with its tag
  (which would break the in-app updater's version compare); and (2) if a release
  re-run takes the "release already exists" branch, it now flips the draft flag
  off — previously a first run that created the draft but died before publishing
  left every retry re-uploading assets to a release that stayed an invisible
  draft forever.

### Changed
- **Python 3.14 is now a supported/tested version.** Added to the packaging
  classifiers and the CI test matrix (3.11–3.14); nothing the project uses was
  removed in 3.14 and PySide6 6.11 supports it. The dev `pytest` pin widened to
  `>=8,<10` so the suite runs under pytest 9 as well.
- **License metadata migrated to the modern PEP 639 form.** `pyproject.toml`
  now declares `license = "GPL-3.0-only"` (SPDX) + `license-files = ["LICENSE"]`
  with `setuptools>=77`, and the deprecated `License :: OSI Approved …`
  classifier was removed. The license itself is unchanged (GPL-3.0-only); this
  just tracks the packaging standard (setuptools now warns on the old
  classifier). Wheel metadata is now Metadata-Version 2.4.
- **Institutional: "validate every input and every dependency output" is now a
  written rule** (CLAUDE.md Code conventions), with the *why it was missing*
  recorded — it had never been documented, which is why Settings inputs had only
  ad-hoc per-widget limits. It's enforced in CI, not left to discipline: a
  **completeness meta-test** fails if any `Config` field lacks a validation rule,
  a **reacts-to-a-bad-value** test corrupts each field to prove it's checked, and
  a **no-shell** guard statically forbids `shell=True`/`os.system`/`os.popen`
  across the tree (so no crafted input can ever reach a shell). See
  `docs/testing.md §5` rule 11 and the Definition of Done.
- **ETA trace now records the *event* behind each jump, and the actual outcome.**
  The `.platterpus.json` `eta_trace` samples already paired the PC clock with our
  smoothed estimate and cyanrip's; each sample now also carries the `track` and
  `activity` (e.g. "Reading track 2… 40%") in effect — so a jump in the estimate
  can be tied to its cause (finishing a fast track and hitting a slow, re-read-
  heavy one) — and at report time each sample is backfilled with
  `actual_remaining_seconds` (the real finish minus that sample's timestamp), so
  the estimate can be read directly against the truth.

## [0.4.8] — 2026-07-01

### Added
- **Auto-fix: an unstable track is now re-ripped on its own, and the better read
  is kept.** When a track's secure re-read didn't converge (read instability),
  Platterpus re-rips **just that track** (cyanrip's `-l`) with a harder `-Z`, into
  a throwaway temp dir so the album's whole-disc `.log`/`.cue` stay intact. If the
  re-read now converges, the improved FLAC replaces the original; if it still
  doesn't, the original is kept and the track stays flagged. **It can never make a
  track worse** — a non-converged read is only ever replaced by a converged one —
  and it needs no speed change (so it works on a speed-locked drive). This
  supersedes 0.4.7's "flag, don't re-rip" for instability, now that a per-track
  re-rip is cheap (seconds, not a whole-disc pass). The results pane reports each
  auto-fixed track (a win) or any that still couldn't be read consistently (a
  caveat). **Hardware-gated:** the re-rip-and-swap path is safe by construction
  but hasn't been exercised on a real drive yet — validate on the BDR-209D rig.
- **Report schema → v5.** `.platterpus.json`'s `read_speed` block gains
  `retried_tracks` (the per-track auto-fix history: each track re-ripped, whether
  it then converged, whether the improved FLAC replaced the original);
  `unstable_tracks` now lists only tracks the auto-fix could not rescue.

### Fixed
- **Read-speed ladder no longer risks aborting the rip on a speed-locked drive.**
  Source review of cyanrip revealed that `-S` (set read speed) is not a graceful
  no-op on a drive that can't change speed — cyanrip prints "Device does not
  support changing speeds!" and **aborts the whole rip**. The maintainer's Pioneer
  BDR-209D reports its speed as `unchangeable`, so an error-triggered escalation
  would have sent `-S 8` and crashed the re-rip (latent since the ladder shipped;
  never hit yet because no disc on that rig has triggered *error*-based
  escalation). The rip log parser now reads cyanrip's `Speed:` banner
  (`RippingInfo.speed_changeable`); when a pass shows the drive can't change
  speed, the ladder **skips the speed rungs entirely and escalates via `-Z` only**
  (the sole lever that works on such a drive), so `-S` is never sent. Pass 1
  always runs at max with no `-S`, so an unchangeable drive is detected before any
  `-S` could be sent — the abort can't occur. Speed-changeable drives are
  unaffected.

## [0.4.7] — 2026-07-01

### Fixed
- **Read-stability was mis-reported as "clean" (real-hardware finding).** On a
  real disc, cyanrip's whole-disc "Ripping errors" count stayed `0` even though
  one track's secure re-read (`-Z`) never converged (5 reads, no two agreed) —
  genuine read instability. The report's `read_speed` block therefore claimed the
  rip was clean (`unresolved: false`). Platterpus now reads cyanrip's **per-track**
  convergence verdict, so an unstable track marks the pass not-clean and is
  flagged as `unresolved` with the specific track listed in `unstable_tracks`.
  Crucially, a *converged* read that merely matches an offset-variant pressing (a
  pressing difference, not a fault) is **not** flagged. Per the maintainer's call,
  an unstable track is **flagged, not auto-re-ripped** — a whole-disc re-rip to
  retry one track can cost hours with no guarantee; only genuine unrecoverable
  read errors still trigger the read-speed step-down. The results pane surfaces
  the caveat too, naming the affected track(s).
- **Update relaunch: "it closed but didn't reopen."** The post-update relaunch
  scrubbed only a fixed *list* of AppImage-runtime vars from the environment, so
  ones it didn't name — notably `QT_PLUGIN_PATH` (and `QML2_IMPORT_PATH` /
  `GI_TYPELIB_PATH` / `GST_PLUGIN_*` / `XDG_DATA_DIRS`) — still pointed into the
  old, about-to-vanish mount, and the new instance aborted on startup (couldn't
  load its Qt platform plugin). The relaunch now scrubs by **value**: any var, or
  any single `PATH`-style segment, that references the old mount is dropped, so
  the new AppImage's `AppRun` sets everything fresh. Session vars (HOME, DISPLAY,
  Wayland/DBus, LANG, …) are untouched.

### Changed
- **One ETA, and it's smoothed.** The status line showed our self-computed album
  ETA while the log still echoed cyanrip's own per-op "ETA - …", so the two
  disagreed on screen. cyanrip's ETA (which we distrust — it once said 822h) is
  now stripped from the forwarded log lines, so only our estimate is shown. That
  estimate is also **smoothed** (an exponential moving average) and **coarsely
  rounded** (bigger buckets for bigger ETAs), so it reads as a steady figure
  instead of jumping every tick.

### Added
- **ETA trace in the report, for posterity + future tuning.** The
  `.platterpus.json` now carries a separate, labeled `eta_trace`: throttled
  samples pairing the PC wall-clock time with the read speed in effect, our
  smoothed album ETA, and cyanrip's own per-op ETA — so both estimates can be
  compared against the real finish (in `timing`) and mined to build a better ETA
  model later. It's kept out of the live UI (analysis data, not display).
- **Report schema → v4.** `.platterpus.json` gains `eta_trace` and
  `read_speed.unstable_tracks` (both described above); `schema_version` bumps to
  `4` so a consumer can tell the new shape apart from 0.4.6's.

## [0.4.6] — 2026-07-01

### Changed
- **One per-album debug file: the JSON. No more `.platterpus.log` sidecar.**
  The album folder now holds only the audio, the front cover, cyanrip's EAC-style
  `<Album>.log`/`<Album>.cue` (for humans), and `<Album>.platterpus.json` — the
  single machine-readable / LLM-oriented artifact. **All** app-generated log info
  for a rip now lives inside that JSON (its `debug.lines` embeds this album's full
  session log, cap raised so a verbose rip is captured whole); the standalone
  plain-text per-album log is no longer written (it only duplicated cyanrip's
  human `.log` and the JSON's embedded log). The always-on global
  `~/.local/share/platterpus/log.txt` is unchanged — it stays *outside* the album
  folder as the cross-session catch-all for program-level failures.
- **The results pane reports the read-speed ladder's outcome (it.1 — usability).**
  When a disc needed a slower re-read (or still had read errors at the floor
  speed), the results pane now says so — a clean single-pass rip stays silent, so
  there's no clutter; an unresolved disc is called out loudly. Screen-reader
  accessible names were also added to the new read-speed Settings controls
  (a11y).
- **The rip report is now written crash-safely (it.12 — resilience).** The
  `.platterpus.json` is written via an atomic temp+rename
  (`os.replace`), the same guarantee `config.save` already gives. Since the report
  is re-written each time a post-rip check finishes, a crash or power loss
  mid-write previously risked a truncated JSON; now a reader always sees a
  complete file (old or new), never a torn one — and a failed write never leaves a
  stray `.tmp`.
- **Unknown-album folder names are hardened across locales (it.11 — i18n).**
  The per-component sanitizer now strips NUL/control characters, refuses the
  filesystem-special `.`/`..` names (so a disc titled `..` can't create a
  traversing/no-op folder), and caps each component at the 255-**byte** filesystem
  limit on a codepoint boundary — so a long CJK or accented title yields a
  creatable folder instead of an mkdir failure. Non-Latin titles otherwise pass
  through untouched.
- **Rip-report writes are debounced.** The post-rip checks (CTDB, FLAC-verify,
  checksums, transcode) each finish independently and each wanted the
  `.platterpus.json` re-serialized with its result — up to ~5 full writes per
  rip. The initial write (the moment the rip ends) is still immediate, but the
  async re-writes now coalesce onto a single-shot timer, so a burst of results
  costs one serialization instead of several. A pending write is flushed on
  window close so nothing queued is ever lost.

### Added
- **Adaptive read-speed ladder — the app now behaves like a careful EAC user.**
  Rips start at the drive's top speed, and only slow down / re-read harder when a
  disc actually reads with errors — quality can only go up, never down. On a pass
  with unrecoverable read errors, Platterpus re-rips the disc a rung slower
  (max → 8× → 4× → 2×, cyanrip's `-S`) and, at the floor, re-reads until repeated
  passes agree (`-Z`), stopping the moment it reads clean or the ladder is
  exhausted — a disc that still can't be read clean is FLAGGED (never papered
  over). A clean disc is a single fast pass, exactly as before. Settings adds an
  advanced "Fixed speed" choice that disables the ladder. Each pass's speed / `-Z`
  / outcome is recorded in the `.platterpus.json` (`read_speed`) and the album
  log. The pure decision logic is unit-tested and never raises. **Three pieces
  are hardware-gated pending validation on the Pioneer BDR-209D rig — whether the
  drive honours `-S`, whether cyanrip's per-track read-error signal is reliable,
  and whether a track subset can be re-ripped; until then the ladder is
  best-effort and cannot cause a regression** (see `docs/cyanrip-fork.md
  §8.1`).
- **Derived files (MP3/WavPack/WAV) are now verified too (Task #19).** The FLAC
  master was already fully verified (AccurateRip + CTDB + `flac --test`); now the
  files we derive from it are proven as well — honestly per format. WavPack and
  WAV are lossless, so we prove **bit-identity**: the derived file and the FLAC
  master are each decoded to PCM and compared, and a difference is flagged as a
  real defect (never papered over). MP3 is lossy, so bit-identity is impossible
  and comparing it would be dishonest — instead we prove it **decodes cleanly
  end-to-end and is complete** (one MP3 per track), and the report says exactly
  that ("decodability + completeness, NOT bit-identity"). Runs off the GUI thread
  after the transcode; the outcome folds into the `.platterpus.json`
  (`verification.derived`, report schema v3) and the results pane. It reuses the
  ffmpeg that already did the transcode — no new dependency (Critical Rule #6).
- **The results pane now shows album loudness + partial-match count.** cyanrip
  already computes the album's integrated loudness (LUFS), loudness range (LU)
  and true peak (dBFS), and how many tracks were offset-variant ("partially
  accurate") matches — but these only landed in the JSON report. A neutral
  one-line footnote under the CTDB verdict now surfaces them (hidden when a log
  carries neither, e.g. a whipper-era log).
- **Year-only naming token `%Y`.** cyanrip's `%y` expands to the *full* release
  date (e.g. `1995-09-12`) and cyanrip has no year-only token, so the two
  "year in the folder" presets used to name a folder `Album (1995-09-12)`.
  Platterpus now has its own `%Y` (the 4-digit year), which the cyanrip backend
  pre-expands to the literal year — taken from the release date the GUI already
  fetched — *before* the template reaches cyanrip. The `Artist / Album (Year)`
  and `Artist / Year - Album` presets now use `%Y`, so a folder reads
  `Album (1995)`. A config still on the old `%y` year presets is auto-upgraded
  (schema v3→v4); hand-edited templates are left untouched.

### Documentation
- Refreshed `docs/eac-parity.md` from whipper→EAC to **cyanrip→EAC**
  (cyanrip is the sole backend since KDD-18): field-by-field for cyanrip's
  header, per-track CRC/AccurateRip/offset-variant, paranoia counts, per-track +
  album loudness, and `Log FUN512:` log signature, plus the single
  `<Album>.platterpus.json` companion (which embeds this rip's session log).
- Documented the **logging model** in `docs/architecture.md §3.7`: the album
  folder holds cyanrip's human `.log`/`.cue` + the machine/LLM `.platterpus.json`
  (which embeds the per-album session log); the always-on global
  `~/.local/share/platterpus/log.txt` lives outside it as the cross-session
  catch-all for program-level failures.

## [0.4.5] — 2026-07-01

### Fixed
- **CTDB verification actually works now — it never did.** We were sending the
  `toc=` lookup parameter with the 150-sector lead-in included (`150:…`), but
  CTDB's `lookup2.php` wants offsets starting at **0** (lead-in removed) — so
  *every* lookup got an HTTP 404, which on some networks surfaced as the "CTDB
  timed out" you saw. Verified against the live server: the corrected `0:…` form
  returns a real match. Also fixed the response parser (the real server returns a
  namespaced document with `crc32`/`hasparity` attributes; we were reading
  `crc`/`hasParity` on a non-namespaced tag and matching nothing), and made the
  lookup **retry transient failures** (timeout/connection/5xx) with backoff while
  never retrying a deterministic 404 — with error messages that distinguish "no
  internet" from "server slow" from "server error." CTDB still fails safe (it can
  never block or invalidate a rip; AccurateRip is the primary proof).
- **The time estimate is no longer nonsense.** The rip report recorded an
  "estimate" of **822 hours** for a 2h38m rip — it captured cyanrip's *first*
  progress tick (at 0.01%, where the extrapolation is meaningless). We no longer
  use cyanrip's ETA at all: the live "about N left" is now computed from actual
  elapsed ÷ album-fraction (stable and self-correcting), and the report records
  the real elapsed plus a **realtime multiplier** (e.g. "2.6× the disc length").
- **The progress line no longer looks like it's going backwards.** cyanrip rips
  each track in a read pass then a "ripping and encoding" pass, each sweeping
  0–100%; the status now says **"Reading track N…"** vs **"Encoding track N…"**
  so the restart reads as expected, and it never echoes cyanrip's jumpy per-pass
  ETA.
- **The verdict now credits offset-variant (partial) matches.** A disc whose
  tracks match an offset-variant pressing (AccurateRip's "+450", confidence-N)
  used to be reported as "aren't in the database or didn't match"; it now says
  e.g. "12 of 14 verified exactly; the other 2 matched an offset-variant pressing
  (partially accurate)" — honest, without claiming bit-perfection.
- **The drive model is captured again.** cyanrip 0.9.3 prints `Device model:`,
  but the parser only matched the older `Drive used:` — so the archival "which
  drive" field came out empty. Both are accepted now.
- **Dialogs now centre over the main window even when they're a plain message
  box.** The 0.4.4 centering only covered our own dialog subclasses, so the
  first-run "add to menu", shortcut, and update prompts (plain `QMessageBox`)
  could still open on another monitor. An application-wide filter now centres
  every dialog — message boxes and file pickers included — on the window that
  opened it. (Still a no-op under native Wayland, where clients can't position
  themselves; the app prefers XWayland, where it works.)
- **The main-window splitter is draggable at the normal window size, not only
  when maximized.** The three stacked panes' minimum heights summed to nearly
  the whole default window, so the splitter handles showed the resize cursor but
  had no slack to move (real-user report on 0.4.4). The scrollable areas (track
  list, rip log, AccurateRip table) now keep a small minimum height, so the
  splitter can always redistribute space. (The default window size is unchanged
  — making it taller would overflow 1366×768 laptops.)

### Added
- **The rip report now captures the loudness, ReplayGain, drive, and log
  signature it was throwing away.** From your real rip: per-track **ReplayGain/
  R128** tags and filename, the whole-disc **loudness summary** (integrated LUFS /
  LRA / true peak), the **drive model** (cyanrip prints `Device model:`, which the
  parser had been missing), and cyanrip's own **`Log FUN512`** signature (its
  analogue to EAC's signed-log checksum — the one archival-forensic field we'd
  been dropping) all now land in the `.platterpus.json`.
- **A readable per-rip debug log now lives with the album** (`<Album>.platterpus.log`),
  scoped to that rip's session with other albums' rips filtered out — the same
  rule as the JSON's embedded copy — so you don't have to dig through the global
  `log.txt`. (The global log.txt stays as the cross-session / no-rip catch-all.)
- The debug log no longer drowns in noise: `musicbrainzngs`' ~40
  "uncaught attribute" lines per lookup are silenced (pinned to WARNING).
- **The `.platterpus.json` is now the single debug record for a rip** — the only
  files a rip leaves are the EAC-compliant `.log`, the `.cue`, and this one JSON.
  It now folds in **all** post-rip verification: the CTDB verdict (as before) plus
  the **FLAC-integrity** decode result and the **transcode** outcome, and a
  **per-file SHA256** map for long-term integrity checking (bit-rot) — embedded
  here rather than a separate `checksums.sha256` sidecar. The report is re-written
  as each async check finishes, so the final file always reflects every one.
- **File-naming presets with a live preview.** Settings has a new "Naming
  scheme" dropdown offering the layouts the popular tools use — *Artist / Album
  / 01 - Title* (the clean default, à la Picard/beets/Plex), a no-dash variant,
  *Artist / Album (Year)* (Plex/Jellyfin media-server style), *Artist / Year -
  Album* (foobar2000 chronological), and a compilation layout that keeps the
  per-track artist. Picking one fills the template fields; hand-editing flips it
  to "Custom". An **Example** line renders the real resulting filename live
  (against a metadata-heavy sample) so you see exactly what you'll get — colons
  and all — before committing.

### Changed
- **Every rip now fully verifies the bit-perfect FLAC master before deriving any
  format.** Verification used to be format-dependent (CTDB only ran under the
  Archival goal). Now all three goals — and a fresh install — run the full suite
  on the master: **AccurateRip** (always) + **CTDB** whole-disc + **FLAC-integrity
  decode**, *before* any MP3/WavPack/WAV transcode. So a portable MP3 is derived
  from a master that's had exactly the same proof as an archival FLAC. The FLAC
  master is always kept. CTDB is now on by default (a network lookup + a decode
  per rip; it fails safe and off-thread, and is still toggleable). The goals now
  differ only in *output* and *compression effort*, never in how hard they check.
- **The default filename layout is now the clean `Artist/Album/01 - Title`.** The
  old default repeated the album and artist in every filename and tacked the full
  release date on the end (`01 - Roxanne - Every Breath You Take… - The Police -
  1995-09-12.flac`). Existing configs still on that default auto-upgrade on load;
  a hand-edited template is never touched.
- The **album-artist field** now has a tooltip explaining it fills every track's
  Artist column and that individual rows can be overridden (for compilations or
  featured guests).

## [0.4.4] — 2026-06-30

*(There is no v0.4.3 — the number was skipped; v0.4.4 follows v0.4.2.)*

### Added
- **Accessibility pass.** Keyboard and screen-reader coverage of the everyday
  surfaces: the album artist/title/year fields and the disc-info values (drive,
  disc IDs, MusicBrainz match, AccurateRip, read offset) now carry accessible
  names — a screen reader announces each by what it holds instead of reading
  anonymous text boxes — and Quit / Settings / User Guide gained the
  platform-standard keyboard shortcuts. (Builds on the verdict/progress surfaces,
  which already named themselves and never signal trust by colour alone.)

### Changed
- **The Start button now explains why it's greyed out.** A disabled button with
  no explanation reads as broken; hovering Start now says exactly what's missing
  and how to fix it — "Insert a disc and choose a drive," then "Identify the disc
  first: pick a MusicBrainz match, or use File → Rip as Unknown Album," and once
  ready, "Start ripping the disc in the selected drive." (general UX principle:
  never leave the user guessing why a control is dead.)
- **The "optional components" prompt no longer looks like a contradiction.**
  After a clean dependency check the app used to show "0 missing/needs-attention"
  and then *immediately* pop a separate "Install optional components?" question —
  which read as "nothing's wrong… so why are you asking me to install something?"
  (real-user report on 0.4.2). Now, when everything required is present, a single
  outcome-first dialog leads with "✓ Everything required is installed — you're
  ready to rip," then lists each optional extra with *what it does for you*
  (e.g. "Picard — auto-launched on unknown discs") and offers to install it. No
  more back-to-back popups.

### Fixed
- **The app no longer freezes while installing a dependency.** Installing an
  optional component (e.g. the Picard Flatpak) ran the install **on the UI
  thread**, so the whole window locked up — unclickable, not repainting — until
  the download finished (real-user report on 0.4.2). The install now runs on a
  worker thread, so the dialog stays live and shows per-row progress; the window
  never freezes. The dialog also refuses to close mid-install (the title-bar ✕
  is gated too, not just Cancel) and is wider so its text no longer truncates.
  Container tools still install through the setup wizard (which has always had
  its own off-thread progress), and only that wizard — not the install loop —
  ever opens on the UI thread.
- **Dialogs now open over the main window, not on another monitor.** On a
  multi-monitor desktop a first-run modal could pop up on a *different* screen
  from the main window; because it was application-modal it correctly refused
  input on the main screen, so the app *looked* frozen even though it was just
  waiting for an unanswered prompt the user couldn't see (real-user report on
  0.4.2). Every dialog now centres itself on the window that opened it the first
  time it's shown, so the prompt appears where you're already looking. (No-op
  under native Wayland, where clients can't position themselves.)

## [0.4.2] — 2026-06-30

### Added
- **The rip report is now a self-contained debug record.** The
  `.platterpus.json` beside the FLACs now embeds this session's log — everything
  since the app launched (setup, dependency probes, the MusicBrainz lookup, the
  read offset, the rip itself) — with **other albums' rips filtered out**, so a
  single file has the full picture for *that* album without the noise of others
  ripped in the same session. The on-disk `log.txt` is unchanged (it stays the
  always-on rolling log, including every rip — the catch-all for problems that
  happen with no rip to attach to, like a failed setup or a crash before any rip
  completes).
- **Two new post-rip buttons** in the results pane, beside "View log": **"View
  report"** opens the `.platterpus.json`, and **"Open rip folder"** reveals the
  album folder (FLACs + `.log` + `.json` + `.cue`). All three stay greyed out
  until a rip finishes.

## [0.4.1] — 2026-06-30

### Removed
- **whipper is gone — cyanrip is the sole ripping backend.** After confirming
  cyanrip needs nothing structural for EAC parity (it already hits AccurateRip
  confidence 200 / bit-perfect on real hardware) and that whipper had no
  functional advantage — only the drive-dependent >587 read-offset *bug* that
  always favoured cyanrip — the whipper backend, its Settings dropdown, its
  whipper-only options (CD-R allow, force-overread, keep-going, the whipper-path
  field), and its container install/export were all removed. The setup wizard
  now installs cyanrip + flac + metaflac only. The drive-setup wizard saves the
  detected read offset to Platterpus's own settings (cyanrip is fed it as `-s`;
  it reads no config file of its own). A legacy `whipper.conf` offset is still
  shown for reference. The backend interface (`RipBackend` ABC) stays so another
  engine could be slotted in later. The `setup-host.sh` / `install.sh` scripts
  install cyanrip + flac (not whipper) now, and the docs (README, DEPENDENCIES,
  PLANNING KDD-18, the user guide, the locked Critical Rules) were updated.

### Added
- **The rip record now captures cyanrip's secure-rerip detail.** A `-Z N` rip of
  a marginal disc writes information the parser previously dropped; it's now
  surfaced in the `.platterpus.json` report (and, where it matters, on screen):
  per-track **rip count** ("after N rips" — how many read passes a track
  needed), the **+450-frame offset-variant** AccurateRip match (`offset_450`;
  cyanrip's "partially accurately ripped" — recorded as data, never counted as a
  plain exact match so the verdict can't over-claim), the **"Tracks ripped
  partially accurately"** summary, the disc's **audio duration** ("Total time"),
  and the **Paranoia status counts** (READ/VERIFY/FIXUP_ATOM/OVERLAP — the
  error-correction activity that explains a slow rip). The status-line fidelity
  summary now notes partially-accurate tracks, so a "12/14 verified" result
  reads as a pressing-offset quirk rather than a bad rip.
- **The rip record now shows actual elapsed time vs the ripper's estimate.**
  cyanrip's on-screen ETA is computed from the current read pass only, so it
  can't see secure re-read passes (`-Z N`) and badly under-estimates marginal
  discs (a real 14-track disc took 2h45m while the ETA sat at "~35m"). The app
  log now records the *actual* wall-clock the rip took — the figure only the GUI
  can measure, since cyanrip logs the disc's audio length and a finish timestamp
  but never its own run time — alongside cyanrip's first ETA so the gap is
  auditable. The `.platterpus.json` report gains a `timing` section
  (`elapsed_seconds`/`elapsed_human`, `started_at`/`finished_at`, and the
  estimate when one was seen).
- **The Platterpus logo now appears in the About dialog** (Help → About), above
  the version and environment details.
- **One dependency dialog instead of several.** A fresh install used to pop a
  separate dialog for each missing piece (the ripper *and* metaflac each opened
  their own). Now every installable missing dependency is a single checkbox row
  (ticked by default) in one "Pending installs" dialog: tick what you want,
  press Install, and watch each row's progress. The dismiss button stays greyed
  out until the install actually completes. Container tools (cyanrip, flac,
  metaflac) install via the one setup wizard — opened at most once even when
  several are missing — and packaged deps (Picard) install in place.
- **The UI locks down during a rip.** While a rip is running, the drive
  selector (and its Refresh/Rescan/Eject), the editable track list, and the
  conflicting menu actions (Settings, Set up drive/Platterpus, Rip as Unknown,
  Check for updates, Uninstall, …) grey out — so nothing can be changed
  mid-rip. Only Cancel, Force stop, and Quit stay available; **quitting during a
  rip force-stops it** (kills the reader so the drive isn't left spinning).
- **`scripts/ctdb_verify.py --calibrate`** — a hardware-validation helper that,
  for a disc that's in CTDB, sweeps candidate offset-guard trims over the
  decoded PCM and reports which reproduces the database CRC, pinning the CTDB
  CRC algorithm against a real disc (`platterpus.ctdb.calibrate`). Developer
  tooling toward flipping CTDB from experimental to verified (KDD-16).

### Fixed
- **CTDB verification now reaches the database.** The lookup was hardcoded to
  `https://db.cuetools.net`, which fails with a TLS hostname mismatch (the host
  serves no valid certificate). It now queries over `http://` like the reference
  CUETools client — correct for a read-only public CRC lookup whose trust comes
  from comparing the returned CRC locally. (CTDB matches still show as
  *experimental* until the CRC algorithm is hardware-validated — KDD-16.) *This
  fixes the `lookup_error` seen on 0.4.0.*
- **Release workflow no longer publishes before its assets finish uploading.**
  The release was made visible (and so seen by the in-app update checker) the
  instant it was created, while the 237 MB AppImage was still uploading — so the
  small `.sha256` the updater fetches first could 404 for anyone who checked in
  that window ("couldn't fetch the update checksum: HTTP Error 404", seen on
  v0.4.0). The release is now created as a **draft**, all assets attached, then
  published atomically — closing the window.
- **`uninstall.sh` now removes the menu entry and icon the AppImage actually
  installs.** It deleted `platterpus.desktop` / `platterpus.png`, but the
  AppImage integrates them under the freedesktop app-id
  (`io.github.rmccann_hub.Platterpus.*`), so the menu entry and icon were left
  behind. It now removes both names, plus any pre-rename `whipper-gui` config,
  logs, desktop entries, and AppImage — for a genuinely clean slate.
- **Documentation and on-screen text now match the cyanrip-only app.** A
  post-removal audit caught text that still described whipper as the live
  ripper: the README's manual-install offset steps told you to run
  `whipper offset find` and hand-edit `whipper.conf` (both gone — replaced with
  the in-app drive-setup-wizard flow and a note that cyanrip uses no config
  file), a stale "Ripping backends: whipper (default)" section, a setup-complete
  message that said "whipper is installed," and a drive-failure hint that cited
  a whipper-only cd-paranoia bug and a removed "Keep going" setting. Many
  code comments that claimed whipper's *current* behaviour were corrected to
  describe cyanrip (with whipper kept only as accurate history).
- **The Tools menu said "Set up Whipper GUI…"** — a leftover from before the
  rename. It's now "Set up Platterpus…".

### Changed
- **The main window's panels are now resizable.** The disc-info panel, track
  list, and the controls + progress/log block sit in a vertical splitter — drag
  the dividers to give more room to the track list or the log, in both normal
  and maximized windows.
- **cyanrip is no longer labelled "experimental."** It's the hardware-validated
  backend (and the recommended one for drives with a read offset over 587, like
  the Pioneer BDR-209D, where whipper has a known bug). The Settings entry and
  help now drop the tag and keep only the real caveats (install it in the
  container; restart after switching). CTDB verification stays *experimental*
  until its CRC algorithm is hardware-validated (KDD-16) — that one is accurate.

## [0.4.0] — 2026-06-29

### Added
- **A machine-readable JSON rip report is now saved beside every rip log**
  (`<name>.platterpus.json`). It captures the drive/rip settings, each track's
  CRCs and AccurateRip result, the overall verification verdict, and (if you ran
  it) the CTDB result — the structured companion to the human-readable log, for
  re-verification, scripting, or attaching to a report. It's re-written to include
  the CTDB verdict once that check finishes. `scripts/rip_report.py` regenerates
  it from any rip log.
- **Settings → Goal presets.** A single "Goal" choice at the top of Settings
  anchors the rest to your intent: *Fast verified* (lossless, AccurateRip-checked
  — the recommended default), *Archival exact* (also CTDB-verify + smallest
  lossless files), or *Portable* (an MP3 copy). Picking one snaps the
  format/verification/quality controls to good values; editing any of them
  switches the Goal to *Custom*. The default matches the previous behaviour, so
  nothing changes unless you choose a different goal.
- **Accessibility pass on the rip screen.** Screen readers now announce every
  status surface by name (the two progress bars, rip status, log output, the
  verification verdict banner, the per-track AccurateRip table, the CTDB result,
  the drive selector, and the track list). The verification verdict is conveyed
  by a leading symbol **and** text (✓ verified / ⚠ partial / ⓘ not-in-database),
  never by colour alone — so colour-blind and screen-reader users get the same
  signal as the green/amber/grey tint.
- **Per-drive trust line: where your read offset came from, and how sure.**
  The disc panel now shows a "Read offset" row for the selected drive — e.g.
  *"+667 — from the AccurateRip list (medium confidence)"* or *"measured on
  this drive (high confidence)"* — so you can see at a glance whether the offset
  is a measurement of your actual drive or a model-list lookup to confirm. If a
  second identical drive is connected, or the recorded offset disagrees with
  what whipper.conf will apply, a plain-text ⚠ warning appears there too — the
  "silent wrong-offset rip" (the classic identical-drive bug) becomes visible
  instead of silent. (UX gap #6.)

  Under the hood this is a new drive-profile ledger (`drive_profiles.py` +
  `drive_profile_store.py`, `~/.config/platterpus/drive_profiles.json`) keyed by
  a stable hardware fingerprint (WWN → serial → vendor/model). It is a **trust
  ledger only**: `whipper.conf` and the `--offset` override remain the sole
  authorities for the offset a rip actually uses (PLANNING.md KDD-23).
  *Applying* a remembered offset per drive (true multi-drive correctness) is a
  separate, hardware-gated change and is not done here.
- **`scripts/render_eac_log.py` — render a rip log into an EAC-*layout*
  comparison log.** Turns a cyanrip/whipper rip log into text that mirrors EAC's
  section/per-track layout so you can `diff`/`meld` it against a real EAC log and
  see the per-track Copy CRCs line up (the readable companion to
  `scripts/eac_parity.py`). It is **clearly attributed and never signed** — the
  first line says it was generated by Platterpus and is not a genuine EAC log,
  and the footer carries an explicit "not signed by Exact Audio Copy" marker in
  place of EAC's checksum. It only ever renders real rip data and refuses to
  fabricate an EAC signature (see `docs/eac-parity.md`).
- **At-a-glance verification verdict banner above the results table.** A single
  bold, colour-coded headline now summarises whether the rip is trustworthy
  without reading every row: green "✓ Bit-perfect: all N tracks verified against
  AccurateRip (confidence X+)" when every audio track matched the shared
  database, amber when only some matched, grey for a disc nobody has submitted
  (e.g. a CD-R — where the per-track Copy CRCs still prove a secure read). The
  wording never over-claims — it only ever reports what AccurateRip actually
  returned (a confidence of 0 / "not present" never counts as verified). The
  CTDB result line below it is now colour-coded the same way (green only for a
  hardware-validated match; an experimental match stays amber).
- **Settings → "Re-rip until reads match" for damaged or marginal discs (cyanrip
  only).** Maps to cyanrip's `-Z N`: each track is re-ripped until that many reads
  produce the same checksum, so a shaky read converges to the bit-perfect result
  instead of landing on a near-miss against the AccurateRip consensus (the
  Track-3-class gap in the EAC-parity work). Off by default — a clean disc doesn't
  need it and it costs time, so the normal secure read (paranoia + retries) still
  handles those. Try **2** if a track won't verify against AccurateRip. The whipper
  backend has no equivalent flag, so the control is greyed out (your value is kept)
  when whipper is selected.

### Removed
- **The one-time `~/.config/whipper-gui` → `~/.config/platterpus` settings
  migration** (the project-rename compatibility shim) is gone, along with its
  `LEGACY_APP_NAME`/`LEGACY_CONFIG_DIR` constants and tests. The rename has
  shipped; there's nothing left to migrate.

### Changed
- **In-app User Guide refreshed** to match the current app: both backends
  (whipper + cyanrip), multiple output formats, and the Output format,
  Verify/Re-compress FLACs, and per-drive read-offset trust-line features.
- **README** now shows the rasterized PNG logo (renders reliably on GitHub) and
  its status reflects v0.3.x with current feature highlights.
- **Clearer, outcome-first wording on two technical Settings/setup labels.**
  The overread toggle now reads "Read past the last track to catch any final
  samples (overread)" (under a "Disc lead-out" label) instead of leading with
  the jargon "Force overread into the lead-out". The drive-setup wizard's
  audio-cache result now explains the *effect* first — "this drive caches
  audio, so Platterpus will read around the cache to keep rips bit-perfect" /
  "this drive doesn't cache audio, so its reads are already trustworthy" —
  instead of "will be defeated for secure rips" / "doesn't need cache-defeating".
  (UX gap #5 — lead with the effect, then the term.)
- **Internal: the backend abstract base class is renamed `WhipperBackend` →
  `RipBackend`** (contributor-facing only; no behaviour change). It is the
  backend-neutral interface that *both* the whipper backend
  (`WhipperHostExportedImpl`) and the cyanrip backend (`CyanripImpl`) implement,
  so naming it after one of its two implementations was misleading legacy. The
  whipper backend itself, `WhipperError`, the `whipper_backend.py` module, and
  the `~/.local/bin/whipper` / `whipper.conf` routing are unchanged.
- **Project renamed to Platterpus** (was "Whipper GUI" /
  `Whipper-GUI-Frontend---CD-Rip`). New tagline: *a secure, EAC-style CD ripper
  for Linux (FLAC, WAV, WavPack, MP3)*. The Python package is now `platterpus`,
  the command and config/cache dir are `platterpus`
  (`~/.config/platterpus`, `~/.local/share/platterpus`), and the freedesktop
  app-id / `.desktop` / AppStream id is `io.github.rmccann_hub.Platterpus`.
  **Your settings carry over automatically:** on first launch Platterpus copies
  an existing `~/.config/whipper-gui` into `~/.config/platterpus` if the new dir
  doesn't exist yet. The `whipper` (and `cyanrip`) *backend* is unchanged — only
  the front-end was renamed. Added a project logo (`assets/platterpus-logo.svg`),
  now used as the window/app icon. The rasterized icon bitmaps are now committed
  too — the 512px `build/python-appimage/io.github.rmccann_hub.Platterpus.png`
  the AppImage bundles, and the hicolor/favicon set under `assets/icons/`
  (16–512px), all regenerated from the SVG by `build/make_icon.py`.

### Fixed
- **The post-rip status line now reports AccurateRip the same way the verdict
  banner does.** When per-track AccurateRip data is available it counts verified
  tracks with the same confidence ≥ 1 rule as the banner (e.g. "AccurateRip:
  12/14 verified") instead of paraphrasing the log's summary line, so the
  one-line status and the banner can't disagree. The in-app User Guide now also
  explains the verdict banner (what green/amber/grey mean) and the new "Re-rip
  until reads match" and "Verify with CTDB" settings.
- **The "AccurateRip" line in the disc panel now agrees with the results-pane
  verdict — and correctly counts cyanrip verifications.** It previously decided a
  track was verified by looking for the words "exact match" in the log, with no
  confidence check. That meant (a) it could disagree with the new verdict banner
  on the same screen, and (b) — because cyanrip writes "accurately ripped,
  confidence N" with no "exact match" wording — it showed "not in database" for a
  disc cyanrip had *fully verified*. Both surfaces now use one shared rule
  (AccurateRip confidence ≥ 1), so the panel and the banner can never contradict
  each other and a cyanrip rip's verification is reported honestly.

## [0.3.10] — 2026-06-27

*(This heading was accidentally dropped in a later edit — the section below had
been absorbed into [0.4.0]. Restored 2026-07-21 verbatim from the `v0.3.10`
tag's own CHANGELOG.)*

### Fixed
- **A colon in an album/track title now ends up as a real `:` in the FLAC tags
  (cyanrip backend).** cyanrip's command line can't carry a literal colon, so the
  app feeds it a look-alike (`∶`) to keep the rip working and the folder name
  clean; a post-rip step now rewrites the *tags* back to a real `:` (e.g. the
  album tag reads "Every Breath You Take: The Classics", not "…∶ The Classics").
  It only runs when a name actually contains a colon, and only the affected tags
  are rewritten — everything cyanrip set (genre, MusicBrainz ID, ISRC, cover art)
  is left untouched. The folder name keeps the `∶` (a real colon in a path is
  best avoided across tools). To fix tags on an album you ripped before this
  release, re-rip it, or run `metaflac` to set the album tag by hand.

## [0.3.9] — 2026-06-27

### Fixed
- **The window no longer goes black during a rip on KDE Plasma 6 (Wayland).**
  This Qt build doesn't repaint a window region that was covered by another
  window and then re-exposed while a rip is running — it went black until you
  interacted with it. On a Wayland session the app now prefers **XWayland**
  (`QT_QPA_PLATFORM=xcb;wayland`), which repaints correctly; the value is a
  fallback list, so if XWayland can't load it drops straight back to native
  Wayland (it can never stop the app from launching). Set
  `QT_QPA_PLATFORM=wayland` yourself to force native Wayland. As a belt, the
  window also forces a full redraw a couple of times a second *while a rip is
  running*, so any stray black region self-heals. (Earlier 0.3.8 throttle helped
  a different, flood-driven case; this is the Wayland repaint cause.)

## [0.3.8] — 2026-06-27

### Fixed
- **Cancel now actually stops a cyanrip rip.** The force-stop only ever targeted
  whipper and its readers (cdparanoia/cdrdao), so cancelling a *cyanrip* rip left
  the in-container cyanrip running — the disc kept ripping after Cancel. cyanrip
  is its own reader, so it's now killed by name too.
- **The window no longer goes black when another window is dragged over it during
  a rip.** cyanrip redraws its progress many times a second, and forwarding every
  redraw to the log pane flooded the GUI's event loop so it couldn't repaint. The
  log pane now updates at most ~10×/second (the progress bar and ETA still move
  smoothly); errors and phase changes are never delayed.
- **The app now relaunches reliably after an in-app update.** The new AppImage was
  being started with the *old* AppImage's environment (`LD_LIBRARY_PATH`,
  `PYTHONHOME`, …), which made the new instance crash silently on launch — the
  "it closed but didn't reopen" report. It now starts with a clean environment.
- **Installing a dependency no longer re-scans the disc.** Finishing setup only
  re-lists drives when none is selected yet (first-time setup); a later install
  (e.g. adding flac) leaves your disc scan alone.

## [0.3.7] — 2026-06-27

### Fixed
- **Albums with a colon in the title no longer produce a corrupted folder name
  on the cyanrip backend.** "Every Breath You Take: The Classics" was coming out
  as a folder named `Every Breath You Take∶album_artist= The Classics` (and the
  rip failed). Cause: cyanrip's command-line metadata parser splits on `:`
  *before* honoring backslash-escaping, so any colon inside a value got
  mis-parsed and injected a spurious key. The colon is now substituted with the
  identical-looking `∶` (U+2236 — the same character cyanrip uses when putting a
  colon in a path), so folders are clean and the parser can't choke. *(Restoring
  the literal `:` in the FLAC tags themselves is a follow-up.)*

### Changed
- **The post-update relaunch is now logged.** After an in-app update, the log
  records when the app spawns the new version, and a spawn that fails now tells
  you (instead of silently closing) so you're never left with no window. The new
  AppImage cold-extracts on first launch, so the new window can take 20-30s to
  appear — that delay is normal, not a failure.

## [0.3.6] — 2026-06-27

### Added
- **Tools → Check dependencies can now install the *optional* components.** When
  Picard or `flac` show as "optional, not installed," the check offers to install
  them on the spot — Picard installs automatically (Flatpak); `flac` is set up in
  the ripping container via the one-click wizard. Both route through the existing
  dependency subsystem (no separate install path). Previously the check only
  *reported* optional components with no way to act.

## [0.3.5] — 2026-06-27

### Fixed
- **The setup now installs the `flac` decoder where the app can find it.** The
  setup wizard installed `flac` in the container (the "whipper + flac" step) but
  never exported it to `~/.local/bin`, so it showed as "optional, not installed"
  and `flac --test` integrity verification (used for rips a backend doesn't
  self-verify, i.e. cyanrip) and the CTDB audio cross-check couldn't run. The
  export step now exports `flac`, and re-running **Tools → Set up Platterpus…**
  repairs an existing install.

### Added
- **Force stop now works during a stuck disc *scan*, not just a rip.** A slow
  drive's table-of-contents read can hold the drive open (the in-container
  reader keeps spinning even after the scan times out, because the kill signal
  doesn't cross into the container). Force stop is now enabled during a scan and
  frees the drive **without ejecting**, so the disc stays in for a Rescan; a scan
  that times out frees the drive automatically. No more dropping to a terminal
  to recover a wedged drive.
- **Help → Open logs folder…** opens the folder containing `log.txt` in your
  file manager — one click to grab logs when reporting a problem, no terminal.

## [0.3.4] — 2026-06-27

### Fixed
- **The first disc scan of a session no longer fails with "whipper timed out
  after 30s."** The first `whipper` call has to start the Distrobox `ripping`
  container (podman cold-start), which on first use after a boot routinely takes
  longer than the old 30s scan / 10s launch-probe caps — both were calibrated
  for a *warm* system. They now budget for a cold container (120s scan, 60s
  launch probe), so the launch probe waits for the container to come up — which
  **warms it** — and the disc scan that follows runs warm and fast. If a scan
  still times out, it now shows a plain-language message pointing at **Rescan
  disc** (a retry against the now-warm container almost always succeeds) instead
  of the raw timeout line. (Real-user report, Bazzite + Pioneer BDR-209D.)

## [0.3.3] — 2026-06-27

### Fixed
- **The in-app updater no longer freezes the window ("Not Responding").** The
  download worker's `progress`, `status`, and `finished` signals were connected
  to local closures / a lambda, which Qt delivers as *direct* connections — so
  they ran on the **worker thread** and updated the progress dialog (and popped
  the restart prompt) from off the GUI thread. Touching widgets off the GUI
  thread is illegal in Qt and deadlocked the window — the freeze that looked like
  "hanging on 100%". They're now **bound methods**, which Qt queues to the GUI
  thread (the same fix already applied to the launch dependency check). **Note:**
  because the *running* version drives the update, this only takes effect once
  you're on 0.3.3 — install 0.3.3 directly (download it from the releases page)
  this one time to escape the loop; in-app updates work normally from there.
- **Update progress bar reflects what's happening.** It shows the real download
  percentage while downloading, then switches to a moving "busy" indicator for
  the quick verify/install steps instead of sitting at a frozen-looking 100%.

## [0.3.2] — 2026-06-26

### Fixed
- **The uninstaller no longer stops at the first problem.** Its steps are
  independent (removing the AppImage doesn't depend on removing the container),
  but a single failing step — most often `distrobox rm` when the container is
  busy — used to cancel everything after it, leaving the AppImage, whipper.conf,
  and shortcuts behind ("uninstall didn't do all"). It's now best-effort: it
  removes everything it can and reports exactly what failed. Your settings + logs
  are still kept if anything failed, so the log survives to debug with — re-run
  the uninstall once the issue is resolved.
- **Missing whipper/metaflac now offer the one-click setup, not a search string
  to paste.** When a tool the app installs itself (whipper, metaflac, flac) is
  missing, the dialog now has a **"Set it up automatically…"** button that opens
  the setup wizard — no terminal, no copying. The copyable search string stays as
  a last-resort fallback. (Previously you got a tier-(c) "copy this and search"
  dialog for tools the app is supposed to install for you.)
- **The setup wizard no longer looks frozen during container preparation.** After
  creating the `ripping` container, the first container entry runs a one-time
  initialization that can take a minute or two; the status line used to sit on the
  previous step's text the whole time, looking stuck. It now shows "checking the
  container…" during that step, and the download/install steps say up front that
  they can take **several minutes** on the first run — so you don't give up partway
  and end up with the rip tool installed in the container but not finished exporting
  to the host (exactly the state the report behind this fix ended in).

## [0.3.1] — 2026-06-26

### Changed
- Maintenance release — **no functional changes since 0.3.0.** Cut so installs
  on 0.3.0+ can exercise the now-fixed in-app updater end-to-end (the KDE
  menu-cache freeze that affected pre-0.2.6 builds is gone — the update flow
  stays responsive through download → verify → install → restart).

### Documentation
- Added the multi-format output (FLAC/WavPack/MP3/WAV) on-hardware validation
  procedure to the test plan as **Test 11**.

## [0.3.0] — 2026-06-26

### Fixed
- **WavPack output now actually works (caught pre-release).** The new WavPack
  transcode passed the wrong ffmpeg output-format name (`-f wavpack`; the muxer
  is `wv`), so real ffmpeg aborted and wrote no `.wv` — the unit tests stub
  ffmpeg, so only a real-binary run exposed it. Fixed to `-f wv` and added a
  real-ffmpeg integration test (skipped when ffmpeg/flac are absent) that proves
  each lossless target decodes back to the FLAC's exact PCM. Same `[Unreleased]`
  cycle as the feature, so no user ever saw it.
- **EAC-parity checker now reads real EAC logs (UTF-16).** EAC writes its
  `.log` as UTF-16-with-BOM; `scripts/eac_parity.py` read it as UTF-8, so every
  character became a replacement char, the parser found zero Copy CRCs, and the
  tool reported a false "NOT parity (0/N)" on a perfectly good rip. Reading is
  now byte-sniffed (`platterpus.parity.decode_log_bytes`: UTF-16 LE/BE BOM,
  UTF-8 BOM, a NUL-heavy heuristic for BOM-less UTF-16, else UTF-8; never
  raises). Found running a real EAC MP3 log through the checker; regression
  tests added (the committed baseline had been converted to UTF-8, which hid it).
- **`--doctor` no longer crashes when the ripper backend is unreachable.** When
  the backend probe failed (e.g. whipper not installed) and no diagnostic host
  was injected — the normal command-line path — the failure-diagnosis code built
  a `HostSetup()` without its required `runner`, raising an uncaught `TypeError`
  that aborted the doctor with a traceback. Ironically this happened exactly when
  the backend wasn't set up, which is the case the doctor exists to diagnose. It
  now constructs `HostSetup(runner=SubprocessRunner())`, so the broken link in
  the host→container→backend chain is named in a clean FAIL report. Regression
  test added (the previously-untested `host=None` production path).
- **Cancel now reliably stops a rip even in the startup window.** If you hit
  Cancel in the brief moment while the rip subprocess was still being spawned,
  the cancel only set a flag — the subprocess wasn't stopped, so the worker
  blocked waiting for the rip to finish on its own (only the 5-second
  force-stop backstop eventually caught it). The worker now re-checks the
  cancel flag the instant it has a process handle and stops it, so Cancel
  takes effect immediately regardless of timing.
- **Launch dependency check now applies its result on the GUI thread.** The
  off-thread launch check connected its `finished` signal to a lambda, which Qt
  delivers as a direct connection — so the result handler (which builds the
  "install this dependency" resolver dialogs) ran on the *worker* thread,
  creating widgets off the GUI thread (a real crash risk; Qt logged
  "QObject::setParent: … in a different thread"). It now connects a bound method,
  which Qt queues to the GUI thread. Found by a headless smoke-run of the real
  startup path.

### Changed
- **Packaging metadata corrected.** `pyproject.toml` now declares
  `Development Status :: 4 - Beta` (was the stale `1 - Planning`, untouched since
  the project was scaffolded — the app has shipped public releases since v0.1.0)
  and adds the `Programming Language :: Python :: 3.13` classifier to match the
  3.11–3.13 CI matrix the package is actually tested on. PyPI display only; no
  code or dependency change.
- **Internal refactor (no behaviour change).** A whole-codebase pass to cut
  redundancy and improve readability, with the test suite green and branch
  coverage held at every step: a shared composition root (`composition.py`) the
  GUI and `--doctor` both build adapters through; a `deps/step_engine.py` module
  for the step-engine types the setup and teardown engines share (the teardown
  engine no longer imports its core types from the setup engine); one
  `workers.start_worker_thread()` helper for the QThread lifecycle wiring that
  eight call sites had each open-coded; and DRY cleanups in `offset_config`
  (one section scanner) and the two ripper backends (one `run_capture`). See
  PLANNING.md KDD-21.

### Added
- **Choose your output format — FLAC, WavPack, MP3, or WAV (new "Output format"
  setting).** Every rip still produces FLAC as the lossless archival **master**;
  when you pick another format the app keeps that FLAC and creates the selected
  format alongside it (a quick background transcode), so you never lose the
  lossless copy. **FLAC** and **WavPack** (`.wv`) are lossless; **MP3** is
  best-quality VBR (`-V0`, ~245 kbps) with tags and embedded cover art; **WAV** is
  raw PCM and can't carry tags or art (the Settings page warns you, and points you
  at WavPack for lossless-with-tags). The transcode runs off the GUI thread, writes
  each file atomically, and never costs you the master if it fails. Uses `ffmpeg`
  (already present wherever the cyanrip backend is), routed through the existing
  dependency subsystem — no new install path. Cover art is embedded in FLAC and
  MP3; WavPack/WAV can't embed it (a tooling limit), so the front cover is always
  saved beside the tracks as `cover.<ext>` for those — every format gets a visible
  cover (see docs/mp3-wav-support.md). New `Config.output_format`.
- **Enforced safety layer (contributor-facing).** New `.githooks/pre-commit`
  hard-blocks committing audio/copyrighted media (Critical Rule #8) — even via
  `git add -f` — so the rule is a guarantee, not just guidance (`dev-setup.sh`
  activates it via `core.hooksPath`; `--no-verify` bypasses for a verified
  CC0/self-generated sample). New committed `.claude/settings.json` adds
  permission `deny` rules for destructive commands (`rm -rf`, force-push) and
  secret reads, plus a session-level audio-staging guard. No end-user-facing
  change.
- **Optional post-rip FLAC re-compression (new "Re-compress FLACs" setting, off
  by default).** whipper encodes FLAC at the tool default (`-5`); turning this on
  re-encodes each output FLAC at maximum effort (`flac -8 -e -p --verify` —
  exhaustive model + coefficient search) after the rip to shrink the files as far
  as flac can. `-e -p` cost a lot of *encode* time for a small extra gain but add
  **no** decode cost (they keep `-l 12`), so they're free in the dimension that
  matters for playback. It's **lossless and verified** — the audio stays
  bit-identical — and `flac` preserves the tags and embedded cover art when it
  re-encodes, so nothing the rip wrote is lost. Each file is swapped in
  atomically, so a failure (or a crash) leaves the original untouched; the step
  is best-effort and runs off the GUI thread (folded into the existing post-rip
  tag/cover thread, so it runs *after* tagging and art). It's skipped for cyanrip,
  which already encodes at maximum compression — the Settings toggle is greyed out
  there with an explanation. **Off by default for a real reason, not just the
  modest size gain:** `-8` uses a higher LPC prediction order (`-l 12`) than
  whipper's `-5` (`-l 8`), which costs a little more CPU/battery to *decode* on
  playback — negligible on modern phones/PCs, but the lighter choice for low-power
  portable players (both levels stay inside the FLAC Subset, so it's a decode-
  effort difference, never a compatibility one). New
  `Config.recompress_flac_after_rip` and a
  `WhipperBackend.produces_max_compression_flac()` capability flag. Shipped flags
  (`-8 -e -p --verify --silent -f -o`) verified current against the xiph spec.
- **Post-rip FLAC integrity verification (new "Verify FLACs" setting, on by
  default).** whipper proves every track decodes back to the read PCM by passing
  `flac --verify` during the rip; cyanrip (FFmpeg) does not, so a cyanrip rip
  lacked that guarantee. After a successful rip the GUI now runs `flac --test` on
  each output FLAC (decode + stored-MD5 check) off the GUI thread, and surfaces a
  loud warning if any file fails. It's skipped for whipper (already self-verified)
  — the Settings toggle is greyed out there with an explanation — and is
  best-effort (a missing `flac` is reported, never fatal). New
  `Config.verify_flac_after_rip`.
- **Richer tags on cyanrip rips (genre, disc number, per-track ISRC).** The
  cyanrip backend was fed only album/artist/title/year/MBID + per-track
  title/artist, so its rips were tagged more sparsely than whipper's. The
  MusicBrainz lookup now also carries the top genre tag, the disc numbering, and
  each recording's ISRC, and these flow to cyanrip's `-a`/`-t` (FFmpeg
  `genre`/`disc`/`isrc`). They are **silent passthroughs** — read from the
  identified MusicBrainz release, not editable in the track table — and
  best-effort (empty when MB has nothing). whipper rips are unaffected (whipper
  tags itself from `--release-id`).
- **Settings + `--doctor` now show the read offset whipper will *actually*
  apply.** Previously the Settings field showed only the GUI's stored copy of
  the read offset; when the whipper backend rips without "Override", the
  authoritative value lives in `whipper.conf` (written by the drive-setup
  wizard or hand-edited) and the two can drift — and a wrong read offset
  silently corrupts every rip. Settings now displays the live `whipper.conf`
  per-drive offset beneath the field, and `--doctor` gained a "Read offset"
  check that reports it (or warns "none set — whipper will refuse to rip"),
  with cyanrip noted as applying the offset directly (`-s`). New never-raises
  `whipper.conf` parser in `offset_config.py`. `--doctor` also now **warns when
  a whipper drive's effective offset is above 587** — the threshold of
  whipper's cd-paranoia bug (KDD-18) — and points to cyanrip, which avoids it
  (advice only; the backend is never silently switched).
- **Preflight / "doctor" check — first-pass test of the rip environment, no CD
  needed.** Run `platterpus --doctor` (or `python scripts/preflight.py`) to
  verify everything the rip pipeline needs *except* the disc read itself: the
  Distrobox→whipper routing actually reaches the backend, the optical drive is
  detected and accessible (a drive lists fine with no disc), the dependency
  tools are present, and the host can reach MusicBrainz / the Cover Art Archive
  / CTDB. Prints a clear pass / warn / blocker report and exits non-zero on a
  hard blocker. When the backend is unreachable it **pinpoints which link is
  broken** (Distrobox not installed / no container backend / the `ripping`
  container missing / the backend not installed-in-container or not exported /
  present-but-misconfigured) instead of a bare "unreachable", so the fix is
  obvious. It knocks out the boring environmental failure modes before you
  insert a disc — a bit-perfect rip still needs a real disc on real hardware.
- **Documentation-currency enforcement (contributor-facing).** `CLAUDE.md` gained
  Critical Rule #7 ("Documentation currency is part of Done") as the always-loaded
  anchor that daisy-chains to the rest; `docs/testing.md §6` Definition of Done
  gained the matching CHANGELOG + session-log/graduation checklist items; and CI
  gained a `changelog` job that fails a push/PR carrying no `CHANGELOG.md` entry
  (opt out with `[skip changelog]` for pure historical-record commits). Keeps the
  project's record from drifting behind the code.
- **App startup smoke test (contributor-facing).** `tests/test_app_smoke.py`
  runs the real `app.main()` entry point headless (offscreen Qt, hermetic — a
  fresh empty config with the subprocess probes + drive listing stubbed) and
  asserts the app composes and comes up (menus + widgets present, clean exit)
  and that the launch dependency check applies its result **on the GUI thread**
  with no cross-thread Qt warnings. This is what would have caught the
  off-thread-apply bug above automatically; nothing previously exercised the
  real entry point.
- **`output_reference/` — EAC parity baselines + checker (contributor-facing).** A
  home for reference rip outputs used to prove bit-perfect parity against Exact
  Audio Copy, laid out as a backend × format matrix (EAC / whipper / cyanrip ×
  FLAC / WAV / MP3). The EAC baseline (extraction **log + cue** for the Police
  test disc) is committed under `EAC_flac/`; the backend dirs are populated
  **only** once a rip's per-track Copy CRCs match EAC's, as proof (priority order
  FLAC → WAV → MP3, tracked in `TASKS.md`). Policy in
  `output_reference/README.md`: comparisons are CRC/log-based and **no commercial
  audio is committed** (public repo + copyright + bloat) — the logs' CRCs prove
  bit-perfection.
- **Parity checker.** `scripts/eac_parity.py` (+ `platterpus.parity` and a
  minimal `parsers/eac_log.py`) auto-detects EAC/whipper/cyanrip log formats and
  diffs per-track Copy CRCs, printing a PASS/FAIL table and exiting non-zero
  unless every track matches — so proving and committing a backend's parity is
  one command. Golden-tested against the committed EAC baseline (14/14 tracks).

## [0.2.8] — 2026-06-18

### Fixed
- **Closing the window during a CTDB verify can no longer crash the app.** The
  opt-in post-rip CTDB verify ran on a `QThread`; if you closed the window while
  it was still looking up / decoding (which can take far longer than the close
  wait), the still-running thread was destroyed and the app aborted. It now runs
  on a daemon thread that reports back via a queued signal and isn't joined on
  close — the same safe pattern as the post-rip tagging and cover-art work.
- **PyPI publishing now actually triggers on a release (CI; contributor-facing).**
  `release.yml` creates the GitHub Release with the default `GITHUB_TOKEN`, and
  GitHub suppresses the events such a token generates — so `publish-pypi.yml`'s
  `release: published` trigger never fired, and v0.2.4–v0.2.7 shipped with no
  PyPI publish attempt. `release.yml` now explicitly dispatches `publish-pypi.yml`
  (a `workflow_dispatch`, the documented exception that always runs) on the
  release tag; the publish runs in its own job so a PyPI problem still can't
  block the AppImage release. (Going live on PyPI still needs the one-time
  Trusted Publisher setup — test-plan Test 7.)

## [0.2.7] — 2026-06-18

### Added
- **CTDB verification after a rip (opt-in, experimental).** A new Settings
  toggle, "Verify with CTDB after a rip", checks a finished rip against the
  CUETools Database — a second, TOC-keyed verification path alongside
  AccurateRip. The result appears as a one-line verdict beneath the
  AccurateRip table. It runs entirely off the GUI thread (the network lookup
  and the local FLAC decode), needs the `flac` decoder for the audio check,
  and is **off by default** (it's a network call). Until the audio-CRC
  algorithm is confirmed bit-exact on real hardware, a match is labelled
  **EXPERIMENTAL** rather than "verified" — the check can only ever
  under-claim (report "no match"), never fabricate a verification.
- **`flac` is now a recognised (optional) dependency.** The dependency check
  (at launch and via Settings → Check dependencies) now lists the `flac`
  decoder used by the CTDB audio check, with guidance to install or export it
  — so enabling CTDB verify without `flac` points somewhere instead of being a
  dead end. It's optional: absent only disables the CTDB audio check.

### Fixed
- **The window no longer freezes while tagging an unknown-album rip.** Writing
  the FLAC tags after a rip (a `metaflac` subprocess per track) used to run on
  the GUI thread, so a multi-track album showed "Not Responding" for tens of
  seconds right when the rip finished. Tagging now runs off the GUI thread,
  sequentially with the post-rip cover-art embed on one background thread (so
  the two never touch the same file at once), keeping the window responsive.

### Changed
- **Test hardening + coverage floor raised to 90% (contributor-facing only;
  no app behaviour change).** Added regression tests for previously-untested
  error/edge paths in the self-update installer (download + install-swap
  failures clean up after themselves), the in-app uninstaller dialog and
  engine (already-running guard, close-while-running teardown, tree-removal
  failures, container-probe failure), and the setup workers (the host-setup
  worker had no tests; drive-setup cancel/partial paths). CI's
  `--cov-fail-under` ratchets 88 → 90.
- **Documentation consolidation (contributor-facing only; no app behaviour
  change).** `docs/` reduced from 15 files to 9 + an `archive/`: `best-practices.md`
  merged into `architecture.md` (one canonical home per engineering pattern);
  `release-testing.md` merged into `test-plan.md` (now "Manual & release
  testing", with the EAC CRC baseline stated once); the research-rerun prompt
  folded into `platterpus-session-start.md` (Step 0); the three dated
  investigation write-ups moved to `docs/archive/` with their durable
  conclusions graduated into KDDs / `DEPENDENCIES.md` / adapter comments.
  `PLANNING.md §3` now points at `DEPENDENCIES.md` instead of duplicating it.

## [0.2.6] — 2026-06-14

### Added
- **Debug logging toggle (Settings).** Off by default; when on, the log file at
  `~/.local/share/platterpus/log.txt` records verbose DEBUG detail (every
  probe, command, and parse step) — turn it on, reproduce a problem, and attach
  the log to a bug report. Applies immediately and on next launch.
- **Launch is fully responsive.** All three startup operations that enter the
  Distrobox container — the dependency check, the drive listing, and reading
  the inserted disc — now run off the GUI thread, so the window appears and
  stays interactive immediately even while a cold container spins up (no more
  "Not Responding" on first launch or when selecting a drive).

### Fixed
- **Disc info from a drive you switched away from no longer overwrites the new
  drive's display.** A late disc-probe result for a previous drive selection is
  now ignored.
- **More GUI-thread freezes removed (proactive, same class as the update
  freeze).** Marking a desktop shortcut trusted (`gio`, GNOME) and the menu
  refresh both ran synchronously inside `integrate()` on the GUI thread; they
  are now fire-and-forget. The launch-time dependency check (which shells out
  to `whipper`, entering the Distrobox container — slow on a cold start) was
  moved to *after* the window is shown, so the window appears immediately
  instead of waiting on a subprocess.
- **In-app update no longer freezes the window ("Not Responding") after the
  download (real-user report).** The post-download menu-cache refresh
  (`kbuildsycoca6`, which can take tens of seconds) was run synchronously on
  the GUI thread, blocking the event loop — so the progress dialog sat frozen
  at 100%, the Cancel button "did nothing", and closing took a long time. The
  refresh is now fire-and-forget, and the updater reports each phase
  ("Verifying…", "Installing — almost done, please don't close…") instead of
  sitting at "Downloading 100%". The Cancel button is retired once the
  un-cancellable install phase begins rather than lingering as a dead button.
- **`uninstall.sh --full` now removes the whole `~/.config/whipper/` directory**
  instead of just `whipper.conf`, so the drive-setup wizard's
  `whipper.conf.bak` backup no longer survives a full uninstall (a real user
  found this leftover after a "fresh" reset). Matches what the in-app
  uninstaller already does.

## [0.2.5] — 2026-06-13

### Added
- **Backend-independent cover art.** When the ripper can't fetch art itself —
  cyanrip rips (the app supplies the tags and bypasses cyanrip's own
  MusicBrainz lookup), and whipper's no-network `--unknown` re-rips — the app
  now fetches the front cover from the Cover Art Archive after the rip and
  embeds it in the FLACs and/or saves it as `cover.jpg`, following the
  existing Cover art setting. The setting is no longer greyed out under
  cyanrip. Art is best-effort: a missing cover never affects the rip.

## [0.2.4] — 2026-06-12

### Changed
- **Releases can be cut by dispatching the Release workflow** (Actions → 
  Release → Run workflow → enter the tag). The workflow creates the tag
  itself, pinned to the built commit — no local tag push needed.

### Fixed
- **The menu offer now fires for an update saved over the old file's path
  (real-user report).** Downloading a new version onto the exact path an
  existing menu entry pointed at made the app think it was fully installed
  — no prompt, no move to `~/Applications`, no desktop icon, and deleting
  the Downloads file then broke the launcher ("Could not find the
  program…"). Integration is now offered whenever the running file isn't
  settled in `~/Applications`, even if a menu entry already matches it.

## [0.2.3] — 2026-06-10

### Added
- **True in-app updates (real-user request).** "Check for updates" no longer
  sends you to a download page: when a newer release exists, the app
  downloads it in the background (progress bar, cancellable), **verifies it
  against the release's published `.sha256`**, installs it atomically over
  `~/Applications/platterpus-x86_64.AppImage`, repoints the menu entries,
  and offers to **restart itself into the new version** (the old session
  closes). A failed or cancelled download changes nothing. Source/pipx
  installs still get the release page (their files can't be swapped).

### Fixed
- **Updates re-offer their menu shortcuts (real-user report).** The
  "add to menu?" offer was suppressed forever after being answered once, so
  a freshly downloaded new version never asked to remake its shortcuts and
  the old menu entry kept launching the old file. Declining is now
  remembered **per file**: any not-yet-integrated AppImage (an update, or
  one whose shortcuts you deleted) gets the offer again.

## [0.2.2] — 2026-06-10

### Added
- **The AppImage installs itself to `~/Applications` (real-user feedback,
  2026-06-10).** Accepting "Add to your applications menu?" (or Tools → Add
  app shortcut) now also MOVES the AppImage out of Downloads into
  `~/Applications` — the standard home AppImageLauncher uses — and points
  the menu/desktop entries there, so clearing your Downloads folder can no
  longer delete the installed app. The running session keeps working after
  the move; future launches come from the menu. If the move fails the app
  integrates where it is (never raises, never loses the file). The
  uninstaller now also removes the `~/Applications` copy even when launched
  from somewhere else.
- **"Rescan disc" button** next to Refresh/Eject (real-user request,
  2026-06-10). Re-runs the disc scan + MusicBrainz lookup for the selected
  drive — the retry for transient scan failures and for discs inserted
  after launch. (Refresh only reloads the drive *list* and keeps the
  selection, so it never re-triggered the scan; previously the only retry
  was restarting the app.)

### Changed
- **Plain-language message for the disc-scan flake.** whipper's known
  cdrdao read-toc failure ("FileNotFoundError: …cdrdao.read-toc.whipper.task",
  typically the disc still spinning up) now reads "The drive couldn't read
  the disc's table of contents — … Click 'Rescan disc' to try again"
  instead of a raw traceback line. Unrecognized errors still pass through
  verbatim.

## [0.2.1] — 2026-06-10

### Fixed
- **v0.2.0's release build uploaded no files.** Two packaging bugs: the
  build script looked for python-appimage's cached `appimagetool` with a
  glob that skipped its dot-prefixed cache directory, so the zsync
  update-information embed was silently skipped; the release upload then
  failed on the missing `.zsync` and aborted before attaching anything.
  The glob now matches the dot-form, and a dedicated "Verify update
  artifacts" workflow step fails early with a clear message if the
  `.zsync` is ever missing again. *(v0.2.0 was superseded without
  artifacts; v0.2.1 is identical plus this fix.)*

## [0.2.0] — 2026-06-09

*(No `v0.2.0` tag exists on GitHub — the release was superseded without
artifacts by v0.2.1, see above. The compare links for 0.2.0/0.2.1 therefore
span `v0.1.0…v0.2.1`.)*

### Added
- **AppImage self-update (the last zero-CLI slice, KDD-17b).** The AppImage
  now embeds standard zsync update-information
  (`gh-releases-zsync|…|platterpus-x86_64.AppImage.zsync`) and releases ship
  the `.zsync` file, so any AppImageUpdate-compatible tool can fetch only the
  changed blocks and verify them. In-app: **Help → Check for updates…** asks
  GitHub (off-thread) whether a newer release exists; if so it hands off to
  `appimageupdatetool`/`AppImageUpdate` when installed, or opens the release
  page — the app never downloads update payloads itself. The `.sha256`
  checksum is generated after the update info is embedded, so it always
  covers the shipped file.
- **`setup-host.sh --cyanrip`.** The CLI bootstrap now mirrors the GUI
  wizard's cyanrip step: enables the GPG-checked COPR inside the container
  only, installs cyanrip, and exports it to `~/.local/bin/cyanrip`.
- **"Uninstall Platterpus" menu entry + `--uninstall` mode.** AppImage
  self-integration now also installs an uninstaller launcher in the
  application menu (under System, not next to the app in Multimedia) that
  opens just the uninstaller via the new `platterpus --uninstall` flag — so
  removal needs neither a terminal nor the main app. Verified all our
  `.desktop` entries already file the app itself under Multimedia
  (`Categories=AudioVideo;Audio;`).
- **In-app Uninstaller (Tools → Uninstall Platterpus…).** Removes everything
  the app installed — menu/desktop shortcuts, host-exported
  whipper/metaflac/cyanrip, the `ripping` container, optionally `whipper.conf`
  and the AppImage file itself, and finally the app's own settings + logs —
  with live per-step progress, a confirmation gate, and per-piece checkboxes.
  **Never touched: your music, and Distrobox/podman themselves.** Settings +
  logs are removed last so a failed step still leaves the log to debug with;
  on success the app offers to close itself. `uninstall.sh` now also removes
  the host-exported cyanrip wrapper (parity).
- **Fidelity verdict + AccurateRip table for cyanrip rips (KDD-18).** New
  `parsers/cyanrip_log.py` parses cyanrip's rip log (EAC CRC32 per track,
  AccurateRip v1/v2 + confidence, preemphasis, drive/offset, ripping-error
  count) into the shared `RipLog`, with format auto-detection — a folder can
  hold logs from either ripper. The post-rip summary is worded around what
  cyanrip actually checks ("all N tracks ripped cleanly, no read errors" +
  "AccurateRip: N/M") instead of claiming whipper's Test/Copy CRC pass, and
  the per-track AccurateRip results table now fills in on both backends.
- **Live progress bars during cyanrip rips (KDD-18).** The rip worker now
  parses cyanrip's `\r`-redrawn progress lines ("Ripping track N, progress -
  X%, ETA - …"), so the overall + task bars move, the current track row is
  highlighted, and the status line shows percentage + ETA — same behaviour as
  whipper rips. Per-track completion lines peg that track's slice of the
  overall bar.
- **cyanrip rips are now driven entirely by the GUI's metadata (KDD-18).**
  The rip snapshots the track table (the MusicBrainz release you picked plus
  any edits) and feeds it to cyanrip via `-a`/`-t`, with MusicBrainz always
  disabled (`-N`): no wrong-release risk, no in-container network needed,
  values with `:`/`=`/`'` safely escaped, and the release MBID recorded as a
  tag. The folder/file naming templates now apply to cyanrip too — whipper
  `%A/%d/%t/%n/%y/%N/%a` tokens are translated to cyanrip's `-D`/`-F`
  `{…}` schemes, so both backends produce the same library layout.
- **One unified Settings page across backends.** Options the selected
  backend doesn't support (under cyanrip: CD-R switch, cover art, overread,
  keep-going, the whipper path) grey out instead of disappearing, with a
  tooltip explaining why and that switching the Ripping backend back to
  whipper re-enables them. Greyed-out values are kept, never cleared.
- **cyanrip backend now identifies discs (KDD-18).** `CyanripImpl.disc_info`
  runs `cyanrip -I -N` (info-only, offline — cyanrip computes the
  MusicBrainz DiscID and CDDB ID locally from the TOC) and the new
  `parsers/cyanrip_info.py` parses the report into the backend-neutral
  `DiscInfo` (IDs, track count, MB submission URL), so the disc panel and
  the GUI's host-side MusicBrainz lookup work identically on both backends.
  Includes a property-based "never raises" test per the testing rules.
- **Host-setup wizard can install the cyanrip backend (KDD-18).** When
  Settings → Ripping backend is set to cyanrip, the setup wizard (and the
  Tools → Set up Platterpus… flow) gains a step that installs cyanrip into
  the `ripping` container and host-exports it to `~/.local/bin/cyanrip`.
  Research finding (2026-06-09): Fedora does **not** package cyanrip (nor
  does RPM Fusion); the install uses the GPG-checked COPR
  `barsnick/non-fed` (cyanrip 0.9.3.1 built for Fedora 42–44 + rawhide) via
  a version-generic `.repo` file — no `dnf copr` plugin needed. Switching
  the backend in Settings now offers to run the wizard if cyanrip is
  missing, and the app prefers the host-exported absolute path when
  constructing the cyanrip backend (desktop launches have a minimal PATH).
- **Institutionalized testing strategy + stronger test infrastructure.** New
  [`docs/testing.md`](docs/testing.md) codifies the approach (testing trophy +
  an explicit real-hardware gate, a five-tier case taxonomy, property/golden/
  fault-injection/mutation guidance, the non-negotiable rules, and a Definition
  of Done). Concretely: **property-based tests** (`hypothesis`) lock in the
  "parsers never raise on arbitrary input" invariant
  (`tests/test_parsers_property.py`); CI now runs **branch coverage with a hard
  `--cov-fail-under=88` gate** (baseline ~91%, ratchets up) across a **Python
  3.11–3.13 matrix**; `pytest-cov` + `hypothesis` added to the `dev` extra and
  `mutmut` documented as a periodic audit. Suite is now 534 tests.
- **Ruff linter + formatter.** Adopted `ruff` (config in `pyproject.toml`:
  rules `E,F,W,I,B,UP`, `E501` off; `ruff>=0.15` in the `dev` extra) with a
  parallel `lint` job in CI running `ruff check` + `ruff format --check`. Fixed
  all findings and raised coverage; the suite is now 525 tests.
- **CTDB verify (Phase 1 — library + validation script).** Clean-room (KDD-16)
  CUETools Database lookup client (`adapters/ctdb_client.py`) and verify logic
  (`platterpus/ctdb/`), plus a standalone `scripts/ctdb_verify.py` to validate
  on real hardware. The `toc=` wire format and the audio CRC are
  hardware-validation-gated (both fail safe — never a false "verified"); the
  GUI wiring is deferred until they're confirmed. See `docs/test-plan.md`
  Test 1. PCM decode uses the host `flac` if present (optional dependency).
- **Manual / hardware test plan** (`docs/test-plan.md`) — a step-by-step
  checklist for everything that can't be validated in CI (CTDB verify/repair,
  `drive analyze`/`offset find` success strings, GUI screenshot, Picard UX,
  PyPI go-live).
- **Automated PyPI publishing.** A new `.github/workflows/publish-pypi.yml`
  builds the wheel + sdist and publishes them to PyPI when a release is
  published (i.e. on every `v*` tag, alongside the AppImage). Uses PyPI
  Trusted Publishing (OIDC) — no stored token. One-time PyPI-side setup is
  documented in the workflow header. It's a separate workflow from
  `release.yml`, so a PyPI misconfiguration can't block the AppImage release.
- **Settings → Ripping backend toggle (cyanrip, Phase 2 start).** You can now
  pick the backend (whipper | cyanrip) in Settings; it's wired to
  `Config.ripper_backend` and applied on next launch. cyanrip is marked
  experimental and still needs to be installed in the container (provisioning is
  the next phase). Completes the user-facing half of making cyanrip selectable.
- **cyanrip backend — Phase 1 (KDD-18).** A second ripping backend
  (`adapters/cyanrip_backend.py`, `CyanripImpl`) behind the existing
  `WhipperBackend` ABC, selectable via `Config.ripper_backend = "cyanrip"`
  (app.py picks the backend; default stays whipper). cyanrip is the actively
  maintained successor and — critically — applies the read offset with its own
  paranoia (`-s`), avoiding whipper's cd-paranoia bug at offsets > 587 that
  fails tracks on the Pioneer BDR-209D (+667). Phase 1 ships the tested core:
  the rip argv builder (`-d/-s/-o flac/-r/-N/-G`), `version`, `find_offset`
  (`-f`), and a backend-independent `/dev`+sysfs drive scan; disc-info parsing
  and naming-template mapping are tracked as the remaining phases in
  `docs/archive/ecosystem-audit-2026-06.md`. Not yet user-selectable in the GUI.
- **Autonomous heal when the ripper can't reach MusicBrainz.** whipper inside the
  container aborts (`unable to retrieve disc metadata, --unknown argument not
  passed`) when it has no network — even for a known disc, because it fetches the
  release online. The GUI already has the metadata from its own host-side lookup,
  so on that specific failure it now **automatically re-rips as an unknown-album
  rip** (`--unknown`, no release-id → no network needed) and tags the FLACs
  locally from the on-screen track list. One retry per Start; surfaced in the
  status line. The `RipWorker` watches whipper's output for the marker.
- **App shortcut: Desktop icon + a re-runnable menu action.** Self-integration
  now also drops a clickable icon in your **Desktop folder** (not just the
  applications menu), and there's a **Tools → Add app shortcut** action so you
  can (re)create the menu + desktop shortcut any time — the first-run offer was
  one-shot, so a dismissed prompt previously left no way to redo it. GNOME
  desktop icons are marked trusted (best-effort) so they launch on double-click.
- **AppImage self-integration on first run — no terminal (KDD-17, step 2).** The
  first time the AppImage runs, it offers to add Platterpus to your
  applications menu (writes a `.desktop` entry pointing at the AppImage, drops
  the icon, refreshes the menu caches) and makes the AppImage executable — so
  after the first double-click it launches from the menu like any installed
  app. Supersedes the manual `install-appimage.sh` for the common case; no-op
  on source/pipx installs. New `appimage_integration.py`; one-time/dismissible
  (`Config.appimage_integration_prompted`).
- **First-run host setup from the GUI — no terminal (KDD-17, step 1).** A new
  **Tools → Set up Platterpus…** wizard (also offered automatically on first
  launch when whipper isn't installed yet) does what `setup-host.sh` did by
  hand: installs Distrobox + a container backend, creates the `ripping`
  container, installs whipper into it, and exports it to the host — with live
  per-step progress and idempotent re-runs. System-package installs use a
  graphical **polkit** prompt (`pkexec`) instead of `sudo`, so no terminal is
  needed; on Bazzite/Silverblue the runtime is preinstalled, so those steps are
  skipped and nothing is prompted. Engine: `deps/host_setup.py` (injectable
  runner, dry-run, fully unit-tested); UI: `ui/host_setup_dialog.py` +
  `workers/host_setup_worker.py`.
- **Read offset is now looked up by drive model (full AccurateRip list, bundled).**
  whipper's `offset find` is unreliable (it failed on a Pioneer BDR-209D even with
  a disc that's in AccurateRip). The drive-setup wizard now resolves the offset the
  way EAC/dBpoweramp do — by the drive's vendor+model — and pre-fills it for
  one-click save, **with no disc and no whipper probe**. The **entire AccurateRip
  drive-offset list (~4,800 drives)** is imported and bundled in-code
  (`adapters/accuraterip_offsets_data.py`, a ~21 KB gzip blob), so it works offline
  for any drive — refreshable via `scripts/update_drive_offsets.py` (which validates
  the parse against the known BDR-209D = +667 before writing). Layered: user CSV
  (`~/.config/platterpus/drive_offsets.csv`) > curated overrides > bundled list.
  whipper's `offset find` is kept as optional verification. New
  `adapters/accuraterip_offsets.py` (`OffsetDatabase`). See
  `docs/archive/offset-investigation-2026-06.md`.

### Changed
- **README leads with a no-terminal install.** A new "Easiest — download one
  file, no terminal" section: download the AppImage, do the one-time "allow
  executing" step (GUI instructions for KDE/GNOME), double-click, and answer the
  first-run prompts (menu integration + the host-setup wizard). The scripted/
  CLI paths remain below for testers and developers; Method A notes that
  `install-appimage.sh` is no longer required (self-integration replaces it).
- **Clear, actionable message when a track can't be read.** When whipper gives up
  on a track after its retries (scratched/dirty disc, or the cd-paranoia
  >587-offset upstream bug), the status now says which track failed and what to
  do — clean the disc, or turn on "Keep going" in Settings to rip the readable
  tracks — instead of a bare "Rip failed".
- **Ripping no longer demands the wizard when the drive's offset is already
  known.** If you hit Start without a saved offset but your drive is in the
  bundled AccurateRip list, the GUI now **applies that offset automatically**
  (your Pioneer → +667), tells you once where it came from, and lets the rip
  proceed — instead of blocking and sending you to the drive-setup wizard. Only
  a genuinely unknown drive still needs the wizard. (The manual/wizard-saved
  offset path is unchanged: set it once, then you're good.)
- **Host-setup wizard: live progress + honest end states (no more "frozen / done
  too soon").** The bootstrap engine now emits a **"⏳ currently doing X…"**
  status *before* each step runs — so during a multi-minute image pull or
  in-container `dnf install` the wizard shows what's happening instead of a
  static bar that looks hung. Slow steps say "this can take a few minutes". The
  finish message now distinguishes **"Everything was already set up — you're
  ready to rip"** (the common Bazzite case, which previously flashed by and
  looked like nothing happened) from a setup that actually installed things, and
  surfaces the failed step otherwise.
- **Documentation audit (2026-06-09).** PLANNING.md caught up with the code
  (directory tree + per-module list now include the host-setup wizard,
  AppImage self-integration, AccurateRip offset lookup, and the cyanrip
  backend/parser; the pre-implementation "future CyanripImpl" sketch replaced
  with the as-built design). TASKS.md gained a **Current plan & priorities**
  section — the live, ordered queue with difficulty estimates — and the
  zero-CLI checkboxes were corrected to match what shipped. README gained a
  "Ripping backends" section; the in-app User Guide documents the backend
  toggle; the hardware test plan gained Test 8 (cyanrip install + parity run).

### Fixed
- **Saving Settings no longer resets the one-time first-run flags.** `to_config`
  rebuilt `Config` from scratch and dropped `drive_setup_prompted` /
  `host_setup_prompted` / `appimage_integration_prompted`, so after saving
  Settings the first-run offers could re-appear on the next launch. Preserved now.
- **Ripping without a configured read offset now stops with a clear popup**
  instead of failing cryptically inside whipper. If no offset is set (neither
  whipper.conf nor the GUI's `--offset` override), Start shows a warning that
  explains an accurate offset is required and offers to open the drive-setup
  wizard — which fills the offset in automatically when the drive model is
  known, or detects it from a CD that's in the AccurateRip database.
- **The app no longer vanishes silently on a startup error.** Drive listing
  (and the rest of startup) ran after the window was shown but outside any
  guard, so an unexpected error — e.g. the drive-list parser choking on
  unhandled whipper output — let the window appear and then immediately
  disappear with nothing logged on screen. Startup is now wrapped: any
  unexpected error (including ones raised inside a Qt slot during the event
  loop, via a `sys.excepthook`) is logged **and shown in a dialog** with the
  log-file path, instead of aborting the process. `DrivePicker.refresh()` also
  now degrades any non-`WhipperError` to an "(error: …)" placeholder so a
  drive-listing hiccup leaves a usable window.
- **Drive-setup wizard:** the manual read-offset spinbox (and its up/down
  arrows) and the **Save offset** button are now locked while detection is
  running, so a value can't be edited/saved mid-detection and race what whipper
  writes. They re-enable when detection finishes.

## [0.1.0] — 2026-06-01

### Added
- **One-command installer (`install.sh`).** A single downloadable file (also a
  release asset) that takes a machine from nothing to a launchable app: sets up
  the host stack (Distrobox + `ripping` container + whipper, via
  `setup-host.sh --no-gui`), downloads the published AppImage, and adds the
  desktop shortcut **plus an "Uninstall Platterpus" shortcut**. Flags:
  `--yes`, `--dry-run`, `--no-host`, `--appimage PATH`, `--build`. The
  uninstall shortcut runs the comprehensive `uninstall.sh` (interactive, with
  options); `uninstall.sh` now also removes the AppImage, its icon, and the
  shortcuts, so it cleanly handles both the source and AppImage installs.
- **AppImage built on every push to `main`** (`.github/workflows/appimage.yml`),
  not just at release time, so a broken build recipe is caught immediately. It
  also runs on demand (`workflow_dispatch`) on any branch, uploading a
  downloadable AppImage artifact for testing branches that have no release yet.
  See `docs/appimage-testing.md`.
- **Help menu.** A new **Help → About** dialog shows the version number plus
  support-relevant info (Python/Qt/PySide6 versions, config/log/whipper paths,
  project & issue links), and **Help → User Guide** opens a built-in,
  task-oriented guide (`platterpus/help_content.py`).
- **Force-stop for a runaway drive.** Cancelling a rip kills the host-side
  process, but the reader runs inside the `ripping` container and podman
  doesn't forward the signal, so the drive could keep spinning for minutes with
  no way to stop it. Cancel now auto-escalates after a short countdown (and
  there's a manual **Force stop** button): it kills the **whipper orchestrator**
  (which otherwise just respawns the reader), `fuser -k`'s the device, and
  ejects — a deliberate, user-approved exception to the "never call into the
  container" rule, scoped to this case only. Validated on real hardware: Cancel
  now stops the drive within a few seconds.
- **Desktop integration for the AppImage** (`install-appimage.sh`, shipped as
  a release asset): adds an app-menu entry + Desktop icon for a downloaded
  AppImage (which otherwise installs no shortcut), with `--uninstall`.
- **First-run read-offset onboarding.** whipper refuses to rip until a read
  offset is configured; a fresh user (especially one with only CD-Rs, who
  can't run AccurateRip auto-detection) would otherwise hit a cryptic error.
  On first launch, if no offset is set (neither in `whipper.conf` nor as the
  GUI's `--offset` override), the GUI now offers the drive-setup wizard once —
  dismissible, and never re-nagged (afterwards it lives on Tools → Set up
  drive…). The wizard gains a **manual-entry fallback**: when auto-detection
  can't run, enter your drive's published offset by hand (linked to
  AccurateRip's list); it's applied via `--offset`, so `whipper.conf` is never
  hand-authored (KDD-15).

### Fixed
- **CI on `main` was red.** Since the T32 change that auto-creates the output +
  working directories before a rip, the whipper-backend argv tests created
  `/music`, which fails as non-root on the CI runner (it only passed in a
  root dev container). The argv-only tests no longer touch the filesystem; the
  one test that asserts directory creation uses a writable temp path.

## [0.0.1] — 2026-05-31

*(No `v0.0.1` tag exists on GitHub today — the earliest surviving tag is
`v0.1.0`. Kept as the historical record; the link points at the releases
page.)*

**First public test release.** A Linux GUI front-end for the `whipper` CD-ripping
CLI, aiming for EAC-equivalent archival quality. Validated on real Bazzite
hardware: a full 16-track rip *through the published AppImage*, with every
track's Test CRC matching its Copy CRC and "no errors occurred".

### What works

- **End-to-end FLAC ripping** through the host-exported `~/.local/bin/whipper`
  (Distrobox routing), with per-track AccurateRip confidence and Test/Copy CRC
  verification reported in the UI.
- **MusicBrainz disc identification** via a dedicated adapter — whipper's
  interactive TTY prompt never surfaces; a release picker handles multiple
  matches, and unknown discs fall back to editable `Track NN` placeholder rows.
- **Drive setup wizard** (Tools → Set up drive…) runs whipper's own
  `drive analyze` + `offset find` and writes `whipper.conf` for you — no more
  hand-editing read offsets.
- **Drive-access diagnostics** (Tools → Diagnose drive access…) classify the
  "no drive" case and hand you the exact `usermod` fix when it's a permissions
  problem.
- **EAC parity Settings:** cover art (fetch/embed/save), force-overread,
  max-retries, keep-going, CD-R support, and a manual read-offset override.
- **Progress + fidelity UX:** an overall progress bar plus a current-task bar,
  an animated pre-track disc scan, and an end-of-rip fidelity verdict.
- **Single-file AppImage** bundling Python + Qt + dependencies (the GUI side
  needs nothing else installed), plus a `pipx`/source path for developers.

### Install & uninstall

- **`setup-host.sh`** — one command bootstraps the entire host stack (Distrobox
  → `ripping` container → whipper + flac → host export), idempotent, with
  `--dry-run` / `--yes` / `--no-gui`.
- **`uninstall.sh`** — layered, safest-first teardown; never removes ripped
  music or the repo without an explicit flag and a typed confirmation.
- `dev-setup.sh` installs a KDE app-menu entry and a desktop launcher; both are
  cleaned up by `uninstall.sh`.

### Known limitations

- The **host stack is required** — the AppImage cannot rip on its own (this is
  intentional; whipper runs inside Distrobox).
- **FLAC only** in v1 (MP3/WAV are backlog). FLAC compression level is fixed at
  whipper's upstream default (`-5`); see the README for a post-rip re-encode
  recipe if you want `-8`.
- `setup-host.sh` is verified by `--dry-run` and smoke tests; the full
  hardware-bootstrap path has had limited real-world runs.
- Linux x86-64 only.

[Unreleased]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.12b6...HEAD
[0.6.12b6]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.12b5...v0.6.12b6
[0.6.12b5]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.12b4...v0.6.12b5
[0.6.12b4]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.12b3...v0.6.12b4
[0.6.12b3]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.12b2...v0.6.12b3
[0.6.12b2]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.12b1...v0.6.12b2
[0.6.12b1]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.11...v0.6.12b1
[0.6.11]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.10...v0.6.11
[0.6.10]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.9...v0.6.10
[0.6.9]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.8...v0.6.9
[0.6.8]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.7...v0.6.8
[0.6.7]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.6...v0.6.7
[0.6.6]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.5...v0.6.6
[0.6.5]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4...v0.6.5
[0.6.4]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b15...v0.6.4
[0.6.4b15]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b14...v0.6.4b15
[0.6.4b14]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b13...v0.6.4b14
[0.6.4b13]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b11...v0.6.4b13
[0.6.4b11]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b10...v0.6.4b11
[0.6.4b10]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b9...v0.6.4b10
[0.6.4b9]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b8...v0.6.4b9
[0.6.4b8]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b7...v0.6.4b8
[0.6.4b7]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b6...v0.6.4b7
[0.6.4b6]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b5...v0.6.4b6
[0.6.4b5]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b4...v0.6.4b5
[0.6.4b4]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b3...v0.6.4b4
[0.6.4b3]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b2...v0.6.4b3
[0.6.4b2]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.4b1...v0.6.4b2
[0.6.4b1]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.3...v0.6.4b1
[0.6.3]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.2...v0.6.3
[0.6.2]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/rmccann-hub/Platterpus/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.21...v0.6.0
[0.5.21]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.20...v0.5.21
[0.5.20]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.19...v0.5.20
[0.5.19]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.18...v0.5.19
[0.5.18]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.17...v0.5.18
[0.5.17]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.16...v0.5.17
[0.5.16]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.15...v0.5.16
[0.5.15]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.14...v0.5.15
[0.5.14]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.13...v0.5.14
[0.5.13]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.12...v0.5.13
[0.5.12]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.11...v0.5.12
[0.5.11]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.10...v0.5.11
[0.5.10]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.9...v0.5.10
[0.5.9]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.8...v0.5.9
[0.5.8]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.7...v0.5.8
[0.5.7]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.6...v0.5.7
[0.5.6]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.5...v0.5.6
[0.5.5]: https://github.com/rmccann-hub/Platterpus/compare/v0.5.0...v0.5.5
[0.5.0]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.24...v0.5.0
[0.4.24]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.23...v0.4.24
[0.4.23]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.22...v0.4.23
[0.4.22]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.21...v0.4.22
[0.4.21]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.20...v0.4.21
[0.4.20]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.19...v0.4.20
[0.4.19]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.18...v0.4.19
[0.4.18]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.17...v0.4.18
[0.4.17]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.16...v0.4.17
[0.4.16]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.15...v0.4.16
[0.4.15]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.14...v0.4.15
[0.4.14]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.13...v0.4.14
[0.4.13]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.12...v0.4.13
[0.4.12]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.11...v0.4.12
[0.4.11]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.10...v0.4.11
[0.4.10]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.9...v0.4.10
[0.4.9]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.8...v0.4.9
[0.4.8]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.7...v0.4.8
[0.4.7]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.6...v0.4.7
[0.4.6]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.5...v0.4.6
[0.4.5]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.4...v0.4.5
[0.4.4]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.2...v0.4.4
[0.4.2]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/rmccann-hub/Platterpus/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/rmccann-hub/Platterpus/compare/v0.3.10...v0.4.0
[0.3.10]: https://github.com/rmccann-hub/Platterpus/compare/v0.3.9...v0.3.10
[0.3.9]: https://github.com/rmccann-hub/Platterpus/compare/v0.3.8...v0.3.9
[0.3.8]: https://github.com/rmccann-hub/Platterpus/compare/v0.3.7...v0.3.8
[0.3.7]: https://github.com/rmccann-hub/Platterpus/compare/v0.3.6...v0.3.7
[0.3.6]: https://github.com/rmccann-hub/Platterpus/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/rmccann-hub/Platterpus/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/rmccann-hub/Platterpus/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/rmccann-hub/Platterpus/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/rmccann-hub/Platterpus/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/rmccann-hub/Platterpus/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/rmccann-hub/Platterpus/compare/v0.2.8...v0.3.0
[0.2.8]: https://github.com/rmccann-hub/Platterpus/compare/v0.2.7...v0.2.8
[0.2.7]: https://github.com/rmccann-hub/Platterpus/compare/v0.2.6...v0.2.7
[0.2.6]: https://github.com/rmccann-hub/Platterpus/compare/v0.2.5...v0.2.6
[0.2.5]: https://github.com/rmccann-hub/Platterpus/compare/v0.2.4...v0.2.5
[0.2.4]: https://github.com/rmccann-hub/Platterpus/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/rmccann-hub/Platterpus/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/rmccann-hub/Platterpus/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/rmccann-hub/Platterpus/compare/v0.1.0...v0.2.1
[0.2.0]: https://github.com/rmccann-hub/Platterpus/compare/v0.1.0...v0.2.1
[0.1.0]: https://github.com/rmccann-hub/Platterpus/releases/tag/v0.1.0
[0.0.1]: https://github.com/rmccann-hub/Platterpus/releases

---

*Last updated for Platterpus v0.6.12b6.*
