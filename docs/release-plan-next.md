# Release plan — the next release, gated on the rig package

**Status: waiting on the maintainer's rig package.** He is ripping now and will
send logs, cue sheets and the JSON report. Nothing releases until that lands and
its findings are folded in — his instruction, and the right call: *"you dont need
to release anything now, but plan to do this all to a new, at least beta, but
maybe more release, as soon as you have the full package. feel free to start now,
but you make more work."*

That last clause is the governing constraint. Work that his data could
**invalidate** waits. Work his data **cannot touch** can proceed. §3 sorts the
queue on exactly that line.

---

## 1. What is already on the branch

Pushed to `claude/session-omka9f`, all green (37 uiscript tests + the full suite,
lint and format clean):

| landed | what it was |
|---|---|
| **v0.6.4b11** | published pre-release: option-label convention, three screens that name the build, the derived `rip_goal`, dialog lifecycle logging |
| Settings scroll fix | `minimumSizeHint` was **739 × 971** — the dialog could not be shrunk *at all*, so OK/Cancel sat below the screen edge. Now 146 px, form scrolls, actions never do |
| uiscript pure layer | vocabulary, parser (never raises, fuzzed), transcript |
| uiscript runner | QTimer state machine; screenshot **plus a window manifest**, because `grab()` returns a valid pixmap for a dialog that was never shown |
| cyanrip passthrough | routed through `run_capture` — the app's own seam — and **sanitised**, after the maintainer's question found it bypassed the argv chokepoint |
| Critical rule #12 extension | bidirectional seam sanitation, institutionalised here and drafted for the fork |

## 2. What the rig package unblocks

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

## 3. The queue, sorted by whether his data can invalidate it

### 3a-0. THE FIRST DELIVERABLE, and what it forces

His directive: *"the first test should be giving copying and pasting in a script
that tests every paramter/arguement, and give back a result. then we should be
able to determine if all is reaching platterpus and cyanrip, then we can go from
there."*

**Right instinct — plumbing before behaviour.** Before asking whether a setting
*works*, ask whether the script can *reach* it at all. A reachability sweep is
the cheapest possible first test and it fails loudly rather than subtly.

**But it cannot be written today, and the reason is my own defect:** `set` and
`expect` — the two verbs a "test every parameter" script is made of — are among
the **13 of 25 that are advertised and unimplemented**. Handing him that script
now would hand him a batch that fails on every line. So §3a.1 and §3a.2 are not
merely "safe to do now", they are **prerequisites of the first deliverable**, and
the order is forced:

> `set`/`expect` on Config field names → the remaining verbs → **generate** the
> coverage script → he pastes it → we read the result.

**The design decision that matters: the script is GENERATED, not hand-written.**
A hand-written "tests every parameter" script is wrong the day a field is added,
and wrong *silently* — it would still pass, just over a smaller surface, which is
the completeness-decay shape `docs/testing.md` §5.af describes. So a
`scripts/emit_uiscript_coverage.py` derives it from the **`Config` dataclass
fields** plus the **verb table**, exactly as `scripts/emit_dependency_contract.py`
already derives our half of the cyanrip contract. Then:

- every parameter is covered **by construction**, not by my diligence;
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

### 3a. Safe to do now — his data cannot change these

1. **The 13 unimplemented verbs.** `verbs.py` advertises 25, `runner.py`
   implements 12. This is `docs/testing.md` §5.p committed by the hand that wrote
   the rule. **Plus the one-line sweep** asserting the two sets agree, which is
   what stops the next one.
2. **`set`/`expect` keyed on `Config` field names, not row labels.** Seven form
   rows have the label `""`, five of them interactive — a label namespace cannot
   reach five real switches. Generalise `settings_dialog.py:700`'s existing
   `_validated_widgets` registry so the resolver, the validation renderer and the
   completeness test share one source. Traps recorded in `TASKS.md`
   (`secure_rerip_dynamic` **inverted**, `update_channel` a bool view of a
   string, U+00D7 and U+2026 in labels, three substring collisions, disabled
   widgets must fail **loudly** rather than no-op).
3. **The return-path sanitiser and the plain-text sweep.** `setTextFormat` has
   **zero** hits across the UI package, so every widget is on `Qt::AutoText`,
   which auto-detects HTML. A MusicBrainz title containing `<` is swallowed in an
   error dialog and the user never learns text went missing. Sweep, don't
   spot-fix.
4. **The console dialog**, gated behind two separate Settings toggles (show the
   console; allow unsafe verbs), plus the Tools menu entry.
5. **Handshake lap 28.** Independent of the rip *except* for the pin verdict —
   draft everything else now: withdraw the stale HOLD (their flag table arrived;
   `_MAX_TABLE_LAG` is 0), correct the recommendation of a pin our own
   `fork_source.py` lists as superseded, raise the three-sends-under-one-lap-number
   protocol breach, and attach the §S seam-sanitation clause already drafted.

### 3b. Wait for the package

6. Read the artifacts; fold every finding into the queue before cutting anything.
7. The `ui_script` block in the rip JSON, **under the 25 MB ceiling** — his
   package tells me how much headroom a real report actually leaves.
8. The pin verdict in lap 28, and whether round 7 can close.
9. Whatever the rip itself surfaces.

### 3c. Last

10. **One release.** Version decided by what lands: another beta if the package
    raises anything unsettled, or the **stable v0.6.4** if round 7 closes on a
    bilateral GO. `scripts/handshake.py --release-gate` decides that, not me —
    a stable release is blocked while a round is open, and that is the deviation
    policy, not a preference.
11. **The single batch script**, written against a vocabulary where every verb
    works. Writing it before §3a.1 would hand him a script that fails on him.

## 4. The release gate — what must be true

- Full suite green with the sentinel at `0`; coverage ≥ 91 %; ruff + mypy clean.
- `pytest tests/test_no_stale_version_claims.py` and `tests/test_doc_version_stamps.py`.
- `scripts/handshake.py --release-gate` — `--prerelease` permits a beta with the
  round open; **stable requires bilateral GO**.
- Every P0 in `TASKS.md` either fixed or explicitly deferred **in writing**.
- The batch script exercised against the real vocabulary, not against the table.

## 4a. The maintainer's stated intent for the release

His heads-up, verbatim: *"after i upload all the new logs and documents, plan to
take those and what we have here, and make a new beta version we can do another
round of handshakes with the cyanrip app, so we can try again."*

That settles the version question §3c left open, and it settles it **downward**:
the next release is a **beta**, deliberately, because its job is to be the
artifact a *new handshake round* is run against. A stable v0.6.4 would be the
wrong shape for that even if round 7 closed — you cannot open a round on a build
whose purpose is to be final.

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

## 5. What could change this plan

Stated so that a later reader can tell a revised plan from a forgotten one:

- **A gap in `eta_trace` during the re-reads** promotes the ETA from "deliberately
  untouched" to a release blocker.
- **A missing `dialog presented:` line** means the picker was created and never
  shown — a different and more serious bug than the logging gap already fixed.
- **A wrong pre-gap result** sends the fork's cue fix back and round 7 stays open,
  which forces a beta rather than a stable.
- **A report near 25 MB** changes the `ui_script` embedding from "include the
  transcript" to "reference it and embed a digest".

---

*Last updated for Platterpus v0.6.4b11.*
