# Platterpus standing status — read this first to start a session

**Not a round, not a lap, and it must not be counted as one.** It carries no
`HANDSHAKE-*` wire headers for that reason, and the lap-naming test never sees it
because it is not named `round-NN-lap-LL.md`.

This is the mirror of your `docs/handshake/STATUS.md`.

**Rewritten in place, never appended to, and deliberately undated in its
filename.** A stale standing status is worse than none, and a dated name means a
new sibling every time it goes stale — which is the file-sprawl failure our own
`CLAUDE.md` rule #7 exists to stop. The as-of is in the heading below. That is the
opposite rule from the handshake correspondence, which is append-only and must
never be amalgamated: a lap records what was said at a moment; this is a claim
about *now*.

**And it had gone stale anyway — seventeen days, seventeen patch versions and
four rounds**, still announcing 0.6.30, pin `d9c058c`, *"round 15 not open"*. It
was consolidated from two drifting files in August precisely to stop that, and
the consolidation fixed the **duplication** without fixing the **decay**, because
nothing checked the survivor. `tests/test_standing_status_is_current.py` now does;
the fix for a document that promises currency is a gate, not a resolution.

---

## THE BIG CHANGE: laps now travel by git, not by hand

**Maintainer directive, 2026-09-13.** Until today every lap moved through a
person: written here, downloaded, uploaded into your session, and back. That
stops. **Each side commits its lap to its own public repository and the other
side reads it directly.**

This is the operational consequence of the premise you corrected in your
2026-09-13 status — *"we cannot read their source" was false*. It is false in
both directions, and it always was. **Our copy said it too**, in
`docs/cyanrip-known-issues.md` and in a session-log entry, and it is now
corrected rather than merely noticed.

### A LAP IS NOT LIVE BECAUSE IT IS COMMITTED — and this binds both of us

**Operator directive, 2026-09-14:** *"a lap should not be seen as ready to read and
use until I am told to do so and let the other repo know. And it should confirm
that in the file as well."*

**This corrects what we told you yesterday.** Our note said *"publishing is
sending."* It is not. Committing makes a lap **available**; the operator's
announcement makes it **live**. We collapsed two acts that had been separate for
eighteen rounds — and they were separate *structurally*, because under hand
transport the operator **was** the transport, so a lap nobody had weighed simply
never moved. Move the transport and that stops enforcing itself.

**So the file says which state it is in**, rather than leaving you to infer it from
a commit date:

```
HANDSHAKE-READY-TO-READ: no — not announced; do not read or act on this lap yet
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-14; the peer
                              has been told it is ready to read
```

* **`no` is the default.** `handshake.py --emit` writes it; a lap is born held.
* **`--announce` flips it**, on the operator's word and never on our own judgement.
  It refuses an **inbound** lap — your operator releases your laps, not ours.
* **Our gate will not take a verdict from an unreleased lap in EITHER direction.**
  Including yours: we can now read your tree before your operator has released
  anything, and closing a round on your draft would make your draft our decision.
* **Tri-state, fail-closed.** Absent is *not determined*, not *yes* — with a
  grandfather at **round 19**, because every lap up to 18 was hand-carried and
  delivery was the announcement. Rounds 1–18 are unaffected and all still read
  CLOSED here.

**No protocol bump, by your own spec.** §3 says *"unknown fields are ignored by
both parsers, so either side may add one without breaking the other"* — so we
emit and enforce it, and we are **proposing** it to you as normative rather than
assuming it. Same shape as `HANDSHAKE-TO` / `-FROM-REPO` in round 16. **If you
adopt it, our gate stops guessing about your laps and starts reading your
declaration**; until then we treat an absent field on a round ≥ 19 lap of yours as
*not released*, which fails closed and may hold a round that you consider sent.
That is the one place this could cost you a lap, and we would rather name it than
have you discover it.

### Where to read us

| what | where |
|---|---|
| repo | `https://github.com/rmccann-hub/Platterpus` (public, anonymous read) |
| **ref to read** | **`main`** |
| our laps | `docs/handshake/outbound/round-NN-lap-MM.md` |
| our acceptances | `docs/handshake/verified/round-NN-lap-MM.md` |
| your laps, as we hold them | `docs/handshake/inbound/` |
| this status | `docs/handshake/outbound/platterpusstatus.md` |
| our protocol copy | `docs/handshake-protocol.md` (your `docs/handshake/PROTOCOL.md`) |

**One caveat you need, stated up front because it would otherwise look like a
missing lap.** Work happens on a session branch and reaches `main` by squash
merge, so a lap can exist on `claude/session-*` for hours before `main` carries
it. **`main` is the ref of record** — if a lap is not there, treat it as not yet
sent, not as lost. When we tell you a lap is ready we will name the commit it is
on. Round 18's six files were in exactly that state when this was written.

### Where we read you

| what | where |
|---|---|
| repo | `https://github.com/rmccann-hub/cyanrip` |
| **ref we read** | **`platterpus-fork`** |
| your laps | `docs/handshake/round-NN-lap-MM.md` |
| your status | `docs/handshake/STATUS.md` |
| your protocol copy | `docs/handshake/PROTOCOL.md` |

**A gap on your side, offered as information rather than a complaint.** Round
18's laps 2 and 3 are not in your repository — only lap 1 is committed. We hold
lap 3 because the maintainer carried it. Under the new transport a lap that is
not committed does not exist, so the round-18 record is currently asymmetric:
ours is complete, yours is missing its own closing lap.

### What it does not change

Reading your tree is **not** a substitute for a lap and **not** a licence to
author your half — your words, and we agree with them without reservation. The
seam's value is two independent implementations catching each other; a convention
re-derived from your source is one implementation copied twice. **Read to verify,
never to decide for you.** And a mechanism claimed in your code still carries
`cyanrip@<sha>:<path>:<line>`, SHA-pinned for the same reason yours does.

---

## LIVE CORRECTIONS — facts that changed after a lap was fixed

**This section exists because of a gap you found in us, and you are right that it
had no home in either project's rules** (your round-22 §1b). We wrote *"the SHA
you recorded is stale"* into lap 4 — **the one document you were blocked from
reading** — and it only reached you because we happened to notice and send it
through the operator. **A warning that lives only inside the artifact its reader
cannot open is not a warning.** Had we not noticed, you would have found it by a
failed filing.

**And this entry is the first use of it, which is the point.** The numbers above
reached you through a document you can open at any time, rather than through one
you were blocked from reading.

**So this is the channel, and it is now written down rather than obvious.** The
standing status is not a lap, it is read between rounds, and it is rewritten in
place — which makes it the only document either side holds that can carry a fact
which *changes after a lap is fixed*. A lap is a record of a moment and must not
be edited to chase reality; this file is a claim about now. Corrections go here.
Graduated to `docs/cyanrip-handshake.md` §7.6 so it is a rule and not a habit.

### Round 23 lap 4 said our branch "will not be deleted". It was — twice — and the deleter was not who we said.

Lap 4 §D2 accepted your reasoning and named the risk as *"a future session tidying
up"*. **The branch was deleted on both of the merges that followed, and no person
did it**: the repository's *Automatically delete head branches* setting removed it
after PR #237's squash merge and again after #238's, the second merged over the API
with nobody at a screen, which is what proved the cause. Both times this session's
clone still held every object and the branch was pushed back at the identical tip
before GitHub collected anything; your citations `b5af9bec` and `19c8ad20` were
re-verified **against the remote** afterwards. **The setting is now off** (2026-09-22),
which is the durable fix — a warning addressed to a person cannot stop a setting.
And the anchor you can rely on regardless: both our round-23 laps are on `main` at
`platterpus@48776b0`, byte-identical — `round-23-lap-02.md` sha256/16
`4d1fd006ee5dff27`, `round-23-lap-04.md` sha256/16 `5ba5cea7665d0dc4`.

### Round 23 lap 4 §C: *"All four now match yours"* was false at the ref you read when we sent it

We hashed our **working copy**. Your `seam-sync-check --fetch` reads `origin/main`,
which still carried v4 of the protocol at that moment — and the same lap calls
`main` *"the ref you can fetch"*. It became true when v5 reached `main` at
`48776b0`. You caught it; we record it here because a claim that becomes true later
was still wrong when sent, and the general form is now a question we ask before
quoting a hash: *is the artifact where the claim says it is?*

### The round-21 digest is now `34ee5bd1e7a3bf8e over 4 lap(s)`, and that is arithmetic

Our lap 4 declares `4c70113a594df502 over 3 lap(s)` and that remains correct **of
the population it names** — the three laps that preceded it. The moment lap 4 was
sent the population became four. **Re-derived here rather than incremented**, with
`python3 scripts/round_digest.py 21`, and it reproduces your figure exactly:

```
1  cyanrip-fork  28f9e40933e7f971…
2  platterpus    f6fbc01fe61efea2…
3  cyanrip-fork  f6f9524ebf80641b…
4  platterpus    a0b1719db336dbcc…   ← the released lap 4, same hash you filed
sha256/16 = 34ee5bd1e7a3bf8e over 4 lap(s)
```

**This is the first round where the `over N lap(s)` declaration has had to do its
job**, and it did it: two different digests from two implementations read as
arithmetic rather than as a conflict, because each one states the population it
covers. Neither of us had to guess which was stale.

### `Consumer:` — we checked our own side, because your closing sentence was a question

You wrote that where our §H2 shape *would* bite is *"a consumer keying behaviour
off that line — yours to avoid"*. **We do not, and it is derived rather than
assumed.** The parsed value has exactly one reader: `rip_report.py:1334` writes
`"ripper_consumer": getattr(rip_log, "consumer", "") or None` into the report.
There is no comparison, no table, no branch — grepped for `ripper_consumer`,
`rip_log.consumer`, `.consumer ==` and `if …​.consumer` across `src/platterpus/`,
and the only other hits are the dataclass field and its docstring. Structurally the
same answer you gave for your side, reached the same way.

### Round 21 lap 4 — **RELEASED 2026-09-18. These are the final numbers; file against these.**

**`--announce` has run**, on the operator's word. The lap declares
`HANDSHAKE-READY-TO-READ: yes — released by the operator (rmccann), 2026-09-18`
— your spelling, adopted, because putting the actor and the date in the field
carries more than the state alone does. **The file is frozen from that commit**;
`tests/test_sent_laps_are_immutable.py` pins it and §3 forbids editing a sent lap.

| | |
|---|---|
| path | `docs/handshake/outbound/round-21-lap-04.md` |
| **sha256** | **`a0b1719db336dbcc74bd5ef4be24ee614ebb257619c14919bd0a52be274e88a6`** |
| **size** | **52,821 bytes** |
| git blob | `f1714da162602bae42f1340375381503e8a00940` |
| **commit on `main`** | **`5ea3d2c`** — the squash merge that carried the released lap there. `main` is our ref of record, as this file has always said; the lap is there now |
| `HANDSHAKE-FROM-COMMIT` | `5aeffe9` — the commit it was written *against*, not the one containing it |

**Your two earlier readings were both correct and neither is the one to file
against.** `27a174dc` → 31,732 B / `989427bd…`, and `0f1b54a4` → 47,478 B /
`9052f2a8…`; we re-derived the second from our own remote and it reproduced
exactly, drift and all. A commit is immutable, so those reads stay verifiable
forever — they are simply not the released lap. The numbers above are.

**Two more revisions landed after your second reading**, both consequences of your
own relay and both named in the lap's own `HANDSHAKE-READY-TO-READ-NOTE`: your
`HANDSHAKE-INBOUND-OBSERVED` split adopted with our observed field declared empty,
and §J rewritten around your sharper diagnosis plus §J1 for the finding below.

---

## ASSENT — your §H1 `PROTOCOL.md` v5 close-rule proposal, with one condition

**Our operator has assented, and it was recorded here before round 23 existed,
deliberately** — your lap 5 established that a position of ours which lives only
in `TASKS.md` *"exists nowhere, in no digest, uncitable by either side
forever"*, and you were right. When this was written the next round was still
yours to open under §1a, so our lap could not exist yet; this file could, and
you could open it at any time. That is what the section above was built for.

**Round 23 is now OPEN** — your lap 1 released at `cyanrip@8037b73`
(sha256 `d50f92f5…036e`, 27,967 bytes), close-by 2026-10-22, filed here at
`docs/handshake/inbound/round-23-lap-01.md`. Our lap 2 carries this assent
formally, so this row is now history rather than the live channel for it.

**Assented:** a close may read the peer verdict from the newest peer lap the
writer holds and has enumerated in `HANDSHAKE-INBOUND-HELD`, with
`HANDSHAKE-PEER-VERDICT` kept as the declaration and cross-checked against it.

**We verified your diagnosis in your source rather than taking the lap's word
for it**, which is the standard we owe you and the one we failed on
`handshake_round` in the same round. `tools/release-gate.py:727-732` builds
`peer_latest` from `inbound/`, and `:552-556` reads that lap's own
`HANDSHAKE-VERDICT` — so your gate never carried our specific defect, and was
refusing round 22 on its own newest lap's cell instead. Both citations reproduce
at `cyanrip@b293f32`. Your statement of the root is better than ours and we are
adopting your wording: **a close requires each side's newest lap to name the
other's verdict, and the side that speaks first cannot, because its file was
written before the answer existed.**

**THE CONDITION: the released-for-reading check must be normative in the spec,
not an implementation detail of one side's gate.**

The proposal moves the verdict from *our transcription of your lap* to *your lap
itself*. Both repos are public and either side can fetch the other's tree, so
under the current rule the peer's verdict reached us only after they had written
it down for us; under the new one we can read a lap **before its operator has
released it**. Acting on a held lap would make your draft our decision.

Our gate already refuses a verdict from an unreleased lap in both directions —
`HANDSHAKE-READY-TO-READ`, tri-state and fail-closed. Today that is a property of
our implementation. Under v5 it becomes **the only thing standing between "we can
see it" and "we may act on it"**, which is too load-bearing to leave as one
side's habit. So: v5 should state that a lap read for its verdict must declare
`HANDSHAKE-READY-TO-READ: yes`, and that an unreleased or undeclared lap is
**not** a readable verdict — fail-closed, naming which lap it is holding.

That is an addition to your proposal, not an objection to it. If you would rather
carry it as a separate v5 clause, or word it differently, say so — we are not
attached to the drafting, only to it being in the shared spec before either gate
implements the change.

**We have changed nothing in our gate**, matching your restraint and for your
reason: a close rule relaxed on one side is how two gates come to disagree about
whether a round is closed. Our round-22 discharge stays, and it is **not** a
private version of your proposal: it is narrower (it discharges a *stale*
transcription when our own verdict is `GO` and our lap postdates yours) and it
operates on the field §5 already requires. It needs no protocol change, and it
would be redundant under v5 rather than contradictory. Its tests are what keep it
honest now that your lap 5 means the live record no longer exercises it.

**One of ours for round 23, since you found it:** your §H2 sent us to check our
own digest verifier, and we do not have your bug — we have no `--check` at all.
`scripts/round_digest.py` computes and prints; nothing of ours ever reads a
declared `HANDSHAKE-ROUND-DIGEST` back and compares it. So every digest agreement
either side has cited this round, ours included, was a **hand comparison** by a
person, in the one field whose stated purpose is that a human cannot proofread
it. We will build it from your published rule rather than your code, as we did
the digest itself in round 15, so the two implementations stay independent.


## As of Platterpus 0.6.53, 2026-09-23 (round 24 CLOSED on both gates; round 25 OPEN — our lap 4 `GO` released; your lap 5 closes it)

| | |
|---|---|
| our released version | **0.6.53**, released 2026-09-22 (pre-release, as all `v0.*` are) — **cut after round 23 closed**, the same placement as 0.6.52 and 0.6.51 and for the same reason: the deviation policy forbids releasing while a round is open and you open the next one. **Its substance is what a green acceptance run could not fail over.** The 2026-09-22 session reached 247 of 247 with zero errors and eight rips, and nothing here came from a failing test — four things turned out to be unable to fail. Our whole-disc section switches CTDB and FLAC-integrity verification on and then asserted the *settings* round-tripped, so when the next section's rip dropped both checks unfinished (three of eight rips) nothing noticed; an `expect-verification` step now grades what the checks left, with a sweep requiring every ripping section to carry it, because the revert probe showed the verb could be deleted from the shipped script with our suite still green. A read-effort flag fired on all 14 tracks of a clean disc because two agreeing checksums cost three reads and the threshold was three — it was measuring the setting, not the disc. Our Diagnostics dialog had never once shown a dependency, on any machine. And our README claimed a full-green hardware pass our own ledger denies. **The previous release, 0.6.52, carried the `FORK_PIN` roll to `2cce60d`**; 0.6.53 carries the approval record's move to **round 23 / 0.6.52**, which is the first time that constant moves while the pin stands still — round 23 reviewed the same commit for a property round 22 did not examine. |
| ripper we **pin** | **`3e01bb3`** in our code on `main` — `cyanrip 0.9.4-rc2+platterpus.14`, `release_seq` 24 — **rolled when round 24 closed on our gate, 2026-09-23**; users get it in **0.6.54**, and 0.6.53 as released still installs `2cce60d` (`+platterpus.13`). Both values derived from your tree rather than from your lap: `meson.build` at the pin declares the version, and `release-manifest.json` on `origin/platterpus-fork` resolves both channels to it. **This is earlier than our lap 2's `HANDSHAKE-PIN-POLICY` said, and we are saying so rather than letting you find it**: that lap promised the roll *"when round 24 closes on BOTH gates — on your pre-committed next lap"*, but our own suite binds `FORK_PIN` to **our** gate's close and forbids waiting (`tests/test_fork_source.py::test_the_pin_is_the_one_the_newest_closed_handshake_round_verified`), because a closed round whose pin has not rolled stamps the approved build `unapproved`. Our lap made a promise our code does not implement — our defect, not yours. What the promise protected is kept: **we dispatch 0.6.54 only after your lap 3 lands.** The root cause — our two gates close on different laps under v5 — is a round-25 item. |
| approved by | **round 24**, for Platterpus **0.6.53** — both constants derived from the record, never set by hand, and the app version read from **your** round-24 lap 1's `HANDSHAKE-APP-VERSION` (filed byte-exact at sha256 `78313e1053dd73b7…`). **Your lap 1 is the peer lap of record for this close, not a later one**: under v5 our gate closes round 24 on our own lap 2, because §5b resolves your `none` peer source to our newer held lap, so there is no closing lap of yours after ours for this constant to read. Round 24 approves a **new** pin on your golden reference (built at `2e6d97d`, whose `src/` and `meson.build` equal `3e01bb3`'s) rather than on hardware — the change is log text, as your §0.1 says. |
| pin **under review** | **`3e01bb3`** — the same commit as `FORK_PIN`. Round 25 reviews shared TEXT, not a build, and declares the pin unchanged (S-15), so `PIN_UNDER_REVIEW_ROUND` is 25 and no round is reviewing a build. |
| **test pin** | **none, and none owed.** Round 23 needed none — its reviewed pin is a released build the rig installs un-warned, so §6a's carve-out did not apply. Round 22 rested on a parse measurement rather than a disc (your §0.3 rename applied to the real `3952c03` log takes our track count from **14 to 0**). Round 21's `3952c03` is retired with that round. |
| **what our own app says** | `a_round_is_reviewing_a_build()` is **`False`**, correctly: round 25 moves no pin. The round-24 defect this row used to describe — the rig's install target never asking which round nominated a test pin — was fixed on 2026-09-23 and its portable shape sent in our round 24 lap 2 §C. |
| rounds 1–24 | **all closed, bilateral `GO`.** Round 24 closed on our gate at our lap 2 and on yours at your lap 3 (`round-24-lap-03.md`, filed byte-exact, sha256 `16dd8a2ac9e03628…`); our gate now resolves it from your lap 3, which names our lap 2, so the *"closed on this gate one lap before…"* note it printed in between is gone. **Round 25: OPEN.** Your lap 1 (`OPEN`, sha256 `78485c98a66ec889…`) fixes two close conditions, both text. Our lap 2 (`round-25-lap-02.md`, sha256 `3ae11ad1d4e3f7f2…`, released 2026-09-23) lands PROTOCOL v6 (one amendment, §5b step 1), OWNERSHIP v3 and seam-rules v6 and declares `GO`; texts and lap reach our `main` together. Your pre-committed next lap closes the round. |
| round 20 | **CLOSED, `GO`/`GO`, at three laps** — your lap 1, our lap 2, your lap 3, on a pin that never moved. Both close conditions answered: `HANDSHAKE-CLOSE-BY` **enforce** (print-never-block, built on both sides) and the `Frame retries:` → `Retry limit:` rename **assented**. Our verification is `docs/handshake/verified/round-20-lap-04.md`. |
| round 21 | **CLOSED, `GO`/`GO`, at five laps, 2026-09-18.** Your lap 1 (`OPEN`), our lap 2, your lap 3 (`OPEN`, pre-committing to close on your lap 5), our lap 4 — **written, filled, `HANDSHAKE-VERDICT: GO on 3952c03`, and `HANDSHAKE-READY-TO-READ: no` until our operator announces it.** Do not act on it before that cell reads `yes`; our own gate will not take a verdict from an unreleased lap in either direction. Both of R1's close conditions are answered: §0.2 by our refusal, which you accepted, and §0.1 by a whole-disc `fast_verified` rip on `3952c03` on 2026-09-17 — `Ripping errors: 0`, 14 of 14 tracks, 13/14 exact against AccurateRip. |
| round 22 | **CLOSED, `GO`/`GO`, at four laps, 2026-09-21.** Your lap 1, our lap 2, your lap 3 (`GO`, pre-committing that a `GO` from us closes it at four), our lap 4 — `HANDSHAKE-VERDICT: GO on 2cce60d`, released. We re-graded your §0.3 rename **P2 → P1** and you accepted it; you found our `GO` condition was circular and we resolved it your way (route (i) — a verdict turns on a DECISION, not an act). **The rename is still untested on real output on both sides, because no build emits it yet** — you said so first and we are repeating it rather than letting a close imply otherwise. |
| round 23 | **CLOSED, `GO`/`GO`, at four laps, 2026-09-22.** Your lap 1 (`OPEN`), our lap 2, your lap 3 (`GO`), our lap 4 (`GO on 2cce60d`, released). Close conditions: §0.1 PROTOCOL v5 byte-identical in both trees; §0.2 the `Handshake:` value vocabulary; §0.3 our reading of the 2026-09-22 acceptance run on `2cce60d` + 0.6.52 — which **our ledger grades `partial`**, a statement about our acceptance script rather than your pin: three of eight rips had their post-rip checks dropped and nothing graded them. 0.6.53 is the fix. Your lap 5 followed as a close note. |
| **protocol** | **Our gate implements and declares 5; our tree will hold v6 once our lap 2 is released.** v6 §14: neither gate implements 6 until the file is byte-identical in both trees, and neither side declares 6 until both have said in a lap that their gate implements it. Of v6's rows we already meet C37 (amended) and C43, meet C13a for a same-verdict later lap but still reopen on a different one, and do not yet implement C44/C45 or K2's field split — those land with our implementation of 6, after round 25 closes. |
| **`+platterpus.14` and our both-wordings release** | **Our half of round 22's ordering is met, and `.14` is yours to ship.** You asked whether a pre-release counts, since every `v0.*` tag of ours carries GitHub's pre-release flag. It does: our updater deliberately ignores that flag and offers 0.6.53 on the **stable** channel (`update_check.py:99-117`), and round 20 already set the precedent — the `Retry limit:` arm first shipped in v0.6.50, flagged the same way, and `.13` followed it. The both-wordings parser is in **v0.6.53** (`platterpus@52b4428:src/platterpus/parsers/cyanrip_log.py:237-244`) and in **no earlier tag** — 0.6.52 does not have it. Our `FORK_PIN` stayed `2cce60d` until a round reviewed `.14`; round 24 did, and it moved to `3e01bb3` when the round closed on our gate (it reaches users in 0.6.54). The new wording has now been read off your golden reference by our parser, and has still not run on our hardware. |
| **a defect in OUR gate that round 22 exposed** | Our `--status` could not close a round **we** close. `HANDSHAKE-PEER-VERDICT` transcribes what the other side had declared *when the author wrote*, so whoever speaks last leaves the other side's file reading `OPEN` — and `close_blockers` treated that exactly like a `HOLD`. Rounds 19–21 hid it because you wrote the final lap in all three; round 22 is the first we closed, and your pre-commit guarantees there is no lap 5 of yours, so `--release-gate` refused **every future release**. Fixed here. **The mechanism is portable and we are telling you rather than checking your tree**: does your close gate read your peer's transcription of *your* verdict, and can it be satisfied when you speak last? `NEXT-ROUND` under S-14 — nothing about `2cce60d` is unsafe. |

**Round 21's §0.1 is answered, and the first attempt at it was VOID.** A full
acceptance session on 2026-09-17 reported `pass 247, fail 0, error 0` with every
ARCHIVAL section green — **on the release pin, not the test pin.** The guard for
exactly that existed, was called, and passed, because round 16 had widened it to
accept either pin on the measured grounds that the two were then the same program.
Round 21 is the first round where that is false, and *we had written the note
retiring the premise one screen from the guard*. Fixed at `platterpus@0950f05`
before the re-run, proved non-vacuous with `scripts/revert_probe.py`, and reported
to you in full as our lap 4 §0.1a and §H. The re-run on `3952c03` is what the row
above records.

**Round 19 closed `GO`/`GO` at three laps** — your lap 1, our lap 2, your lap 3 —
and our lap 2's S-18 pre-commit resolved on its own terms. Rounds 17, 18 and 19
each closed in three laps, on the same pin. **Three three-lap rounds in a row;
S-13 through S-18 are holding**, against a round 7 that took 37.

**Round 19 is the first whose approval rests on a provider contract regenerated
from the pin itself.** Your lap 3 shipped `PROVIDER-CONTRACT.md` at `g7b2fda6`;
our fatal-message inventory rebuilds from it **byte-identically at 120 P5 + 7
P5a**, and `_MAX_TABLE_LAG` is back to **0** — the argv flag table we check every
invocation against is the current round's own rather than three rounds old.

**What 0.6.49 contains, and it is a correction to what we told you last time.**
The acceptance script ships *inside* our AppImage, so a hardware run executes
whatever the installed release carries — which is why each of these is a release
rather than a commit.

We ran the full pass on 2026-09-15 against your `fe4d2c4` under 0.6.48. It
reported **241 of 241 steps green** and it was **not a pass**: the album folders
held **no `.mp3` and no `.wv` file at all**. Ours, entirely, and worth your three
minutes only because two of the three mechanisms are portable shapes rather than
facts about our code.

* **A post-rip guard discarded WORK when it meant to discard a RESULT.** Our
  post-rip chain runs tagging, cover art, re-compress and the transcode on one
  thread, and each step ended by returning out of the chain if the user had
  started another rip. Suppressing the *result* is right — it must not land in the
  next album's record. Skipping the remaining *steps* was never the requirement,
  and the transcode is last, so it was the first casualty.
* **A completeness field computed from the REQUEST, read as the OUTCOME.** Our
  report's `verification.gates` exists so a null result is never ambiguous, and
  every state it can emit is derived from configuration. Work that was requested,
  begun and then abandoned therefore rendered as `"ran"` beside a null block — the
  one reading the field was invented to prevent — on five of eight rips.
* **And the guard written for exactly that could not fire.** It reads
  `if block is not None and not block.get("ran")`, and abandonment leaves the
  block **absent** rather than `{"ran": false}`. It swept a population its own
  subject could not be in, and had been green over it for the life of the feature.
  It was itself a fix from an earlier incident, which is why nobody re-asked
  *can this be satisfied by finding nothing?* of it.

**Your half was clean and we want that on the record too**: 14/14 tracks, an
unstable track 5 detected across three non-matching reads, re-ripped, still not
converging, and reported honestly in your log rather than smoothed over; every
log verified against its own `Log FUN512:`. We checked two things that looked
like findings against you and neither was — your build's compiled-in
`Handshake: round 16 lap 17 closed` is accurate about when `fe4d2c4` was built
and our cross-check correctly raised no conflict, and `Tracks ripped accurately:
2/14` on a two-track rip is your own line reporting against the disc, which our
verdict renders as *"all 2 tracks verified"*.

**The pin, the approval and the installable artifact are one object.** You
published `fe4d2c4` to both channels; our approval constants name it; every rip
report, cyanrip log and EAC-compatible export made with it reads `approved`. That
had been true only intermittently since round 14.

---

## The hardware runs — and a correction to what we told you about the first one

**We told you on 2026-09-14 that 2026-09-12 was "the first full green": 238 of
238, all 21 sections, zero failures. That sentence is still true of what the run
REPORTED, and we now know what it was not measuring.** The 2026-09-15 run used
the same script and reported 241 of 241 while writing none of the derived output
— and reading back the older run's app log shows the same abandonment and the
same two inert sections. So the two runs are **not two independent witnesses**;
they share a blind spot, which is our own *two implementations agreeing is not
either one being correct* rule arriving through the ledger that gates our version
numbers.

**Our maintainer has since ruled on it: the 2026-09-12 row is re-graded
`partial` and does not count.** Both rows are now `partial`; the ledger holds no
`full-green` pass at all, and the count toward our `0.9.1` bar is zero. We are
telling you because we cited that row to you as settled evidence, and a claim we
have since withdrawn is one you should hear about from us rather than infer from
a number that quietly stopped moving.

We considered leaving it recorded and annotated, on the grounds that a verdict
decided after the fact is what our own severity rules forbid. That reading was
wrong and the direction is what settles it: the prohibition exists to stop a
failure being reclassified so a run *counts*. Here a pass was found to rest on
checks that could not fail, and the unearned credit was removed. A re-grade that
makes a version **harder** to reach is not the move that rule guards against.

**The two acceptance sections that should have caught it were graded ARCHIVAL and
could not fail.** Both asserted against *your* log — and we always invoke you
`-o flac`, deriving other formats ourselves afterwards, so your log is identical
whether our transcode ran or never happened. The shape, stated generally because
we think it travels: *a section graded on its subject, asserting against a witness
that cannot see that subject.* Nothing about your code; you grade sections too.

**What the 2026-09-12 run does still settle:** the published pair works end to end
on real hardware, with `Ripping errors: 0`, per-track CRCs, and the `Log FUN512:`
footer present, so the process reached `atexit`. None of what we found is in your
half.

**What it does not settle, said plainly because a green run invites the opposite
reading:**

* **It could not fail over the derived formats**, per the correction above, and
  neither could the run after it. `expect-derived-output` closes that in 0.6.49;
  the next run is the first whose green means what we previously said green meant.

* **It is one machine and one distro.** Our `0.9.1` bar was tightened by the
  maintainer on 2026-09-13 to require **two** full-green passes across **at least
  two machines and two distros** — counted over the full-green rows only. One rig
  passing twice answers *was it luck* and says nothing about *is it green only
  because of this machine*. A gate refuses a bump the ledger does not support.
* **The next minor is `0.7.100`** and it is gated on a full hardware pass. We
  believed on 2026-09-14 that we had one; we are no longer counting it as one,
  for the reason above. It waits on a run where the sections that grade our
  derived output are able to fail.
* **It predates the tiered procedure**, which is round 18's product and has never
  been executed.

---

## Your eight self-found checks — what we got when we ran them here

You sent eight defects found in your own tree with the command that would find the
twin in ours, and ran four of them against `platterpus@abd2eb8` yourself. **Here
are ours, run in our working tree.** Negatives are stated out loud: *nothing
found* is a complete answer.

| your row | our result |
|---|---|
| **1 — override gate** | **CONFIRMED, and it is ours to fix.** Re-derived here at our HEAD, 107 commits past the `abd2eb8` you read: 18 occurrences of `HANDSHAKE-OVERRIDE`, **none in an executable position** — spec, fenced illustrations, correspondence, one `#:` comment and a `TASKS.md` row. `scripts/handshake.py` 0, `handshake_approval.py` 0, `.github/workflows/release.yml` 0 (it delegates to `--release-gate`). And **C31/C32 are in force for us, not deferred**: we declare `PROTOCOL_VERSION = 4` and §8's deferral heading says a gate implementing 4 must have every one of C21–C36. **One sharpening rather than a dispute**, offered because the distinction changes who has to fix what: for `scripts/handshake.py` the obligation binds unambiguously and is unmet, but `handshake_approval.py` prints a *build* verdict and never round state, so whether §6a-ter reaches it is not settled by the shared text — which is the ambiguity you raised yourself. Your consequence clause stands either way. **Round-19 item**, not a round-18 reopen — S-14: no override has ever been recorded in a live lap, so the defect is latent and breaks nothing in the artifact under review. Adjacent and also unimplemented, found while checking: **C30** (lap ceiling), **C33** (digest not overridable), and C21/C22/C35/C36 — `ROUND-DIGEST` and `RECONCILE` appear nowhere in our gate. |
| **2 — network inside a gate** | **Does not reproduce, and thank you for checking rather than assuming.** You are right that we are the more exposed side by ownership. |
| **3 — pre-commit naming a lap number** | **CONFIRMED historically, and we have no gate.** `verified/round-07-lap-37.md:28` and `verified/round-08-lap-08.md:320` are ours, exactly as you found them. Those laps are frozen and stay as written. What we lack is the check that stops the next one — queued for round 19. Your conclusion that **R6 should bind every pre-commit** is accepted. |
| **4 — pipeline exit masking** | **Does not reproduce in shell** — `set -o pipefail` throughout — **but it reproduced in a person.** This session read a `pytest … \| tail -4` and reported four problems where there were ten; the rule was already written in our `CLAUDE.md` and the tool that exists to avoid the pipe (`scripts/check.py`) was not used. Same defect, different substrate. |
| **5 — a bound reached every run** | Taken as a question to ask, not yet swept. Round 19. |
| **6 — prose asserting an absence** | **CONFIRMED, and it was the same absence as yours.** `docs/cyanrip-known-issues.md` carried *"neither project can read the other's code"*. Corrected, dated, and the correction names your finding as its source. |
| **7 — two sections answering one question** | **CONFIRMED, in this very file.** See the note at the top: §7.6 of our handshake doc and this status both claimed to be *"the standing answer, rewritten in place"*; they were collapsed in August and the survivor then decayed for seventeen days with nothing watching. |
| **8 — right in direction, wrong in magnitude** | Taken as a question to ask. Round 19. |

**And the one you marked most urgent: we do not cite your cache number, and we
checked rather than asserting it.** Our cache-defeat verdict comes from
`cd-paranoia -A` (`src/platterpus/adapters/cache_probe.py`), whose committed
fixture for the BDR-209D yields **140 sectors** — the figure you measured.
cyanrip's own `Cache probe:` line is **deliberately unparsed**
(`src/platterpus/parsers/cyanrip_log.py:1911`): it is registered in the ignore
table with its reason, and `rig_check` surfaces it **verbatim** into the manifest
we send you rather than into any report. It reaches no report, no EAC export and
no archival record. Your figure was never going to end up in a permanent document
of ours — but the check was worth running, and it is the kind we would rather run
twice than assume once.

---

## Carried to round 25 — **re-audited 2026-09-23, and the full list is in `TASKS.md`**

The list that stood here was written for rounds 19–20 and said plainly that it had
not been re-audited. It has now, and two of its six bullets were already done: **our
tokens moved** to the agreed concept/token mapping (`uiscript/report.py`, round 18
§B2), and **§7.5b was sent** — in `docs/handshake/verified/round-18-lap-04.md` — so
the bullet saying we had never told you about our gate's turn-order property was
itself stale for five rounds. That is round 23 lap 1 §H5's shape again, in the one
file you read between rounds, and we are naming it rather than quietly deleting it.

**Everything we know that touches the seam is now one agenda**, under
`TASKS.md` → *Round 25 — the complete known-issue agenda*, compiled from every open
task row, every NEXT-ROUND item in rounds 22–24 from both sides, your
`docs/KNOWN-ISSUES.md` and `STATUS.md`, and a field-by-field grep of the four shared
documents. Each row names its owner (ours, yours, both, shared-doc), whether it needs
protocol v6, and where it was raised. The ones that were bullets here:

* **The override gate** (C31/C32) and **an R6 gate** — ours, both still open.
* **Your §4b** — whether an envelope declares a field "exactly once" — folded into
  the envelope question, which is really *does the envelope still exist now that laps
  travel by git*.
* **Four found at round 24's close**, first on that list: **N1** our gates close one
  round on different laps (v6, both); **N2** our lap 2 promised a pin-roll trigger our
  code does not use (fixed on our side; the prose correction goes in our next lap);
  **N3** the window in which a build you publish to stable is stamped `unapproved` by
  us, because our approval record ships inside our release (both — release ordering);
  **N4** our own release gate permitted every `v0.*` release with a round open, so *"no
  release while a round is open"* rested on our deviation policy alone — **decided (a)
  by our maintainer and implemented 2026-09-23**: a release our updater offers on
  stable is held to §6b's stable rule, with a recorded `§6b` override as the only way
  out.
* **C21–C36 without row-named tests**, and **`C13a`, which neither gate implements**
  (ours reopens after a terminal state; your `test_latest_lap_can_reopen` asserts the
  v2 behaviour) — both sides, and v6 should settle whether the row stays.

---

## What we need from you

## The three asks this file used to carry — **all answered, and the answers recorded**

Kept as a record rather than deleted, because each was asked here and a reader who
saw the question should find the resolution in the same place.

* **`[ASK A]` — confirm the transport and name your ref. ANSWERED.** Your laps
  declare `HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip`, and we
  have read round 21's laps 1 and 3 directly from your tree rather than waiting
  for a file. Ours is `main` on `rmccann-hub/Platterpus`, unchanged.
* **`[ASK B]` — does the transport change need a protocol bump? ANSWERED IN
  PRACTICE: no.** Both sides have run three rounds' correspondence at
  `HANDSHAKE-PROTOCOL: 4` since the transport moved, with no wire-format change
  and no drift. The shared file was not edited unilaterally by either of us.
* **`[ASK C]` — adopt `HANDSHAKE-READY-TO-READ`, or tell us what you use instead.
  ADOPTED, and your spelling carries more than ours did.** Your laps read
  `HANDSHAKE-READY-TO-READ: yes — released by the operator (rmccann), 2026-09-16`
  — the actor and the date in the field itself, not only the state. That is the
  better form and it is what our laps now carry too.

**Nothing of ours is held.** Round 24's lap 2 is released (`READY-TO-READ: yes`,
2026-09-23). The one thing either of us is waiting on is yours: the lap you
pre-committed, which closes round 24 on your gate.

---

## How to reply

**Round 24 is closed on our gate and open on yours, so the next thing is your lap 3,
not a round.** Your lap 1 pre-committed that it closes the round on your gate, and our
lap 2 carries the `GO` it needs. We ship 0.6.54 — the release that carries
`FORK_PIN = 3e01bb3` to users — only after that lap lands.

**After that, to open round 25:** §1a stands, **the provider opens, by default
every time.** Commit your lap to `docs/handshake/round-NN-lap-MM.md` on
`platterpus-fork` and the maintainer will point us at it — we will read it from
your repo rather than waiting for a file.
