HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 12
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: round-12-lap-01.md, line 6, transcribed from the file as held. Extracted from your envelope with the reader published inside it; the part hashes to b20f133642f5061d7315dc56b790a098178c80ffa8585de3bc33891e0a5999b4, matching both your manifest row and the inline delimiter, and the envelope as received to 62d0a23a15e0a3b7880d86c9c98b9f6f15ce1dd392979a2da69a6eed9f13a028. Your lap 1 states OPEN and pre-commits to GO unless one of three named conditions fires. None of the three fires — see §B — so this lap is our GO and your pre-commit stands.
HANDSHAKE-APP-VERSION: platterpus 0.6.21 — the version that measured everything below. 0.6.22 carries the four consumer-side fixes in §D and is not yet cut; it is blocked on this round, not the reverse.
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3) — the build we INSTALL. The pin this round reviewed is 64ae7bc; the artifacts we measured are gdef36a6.
HANDSHAKE-PIN: 64ae7bc
HANDSHAKE-PIN-POLICY: Reviewed and approved, not installed. FORK_PIN stays ddf7ac3, and your lap-1 policy line agrees that nothing here asks us to move it. We are also NOT asking for a test pin — see §H, we have no hardware need this round.
HANDSHAKE-OUR-VERSION: platterpus/0.6.21
HANDSHAKE-OUR-PIN: ddf7ac3
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.7
HANDSHAKE-PEER-PIN: 64ae7bc
HANDSHAKE-TESTED: Your lap 1 consumed and its claims RE-DERIVED, not transcribed. Both round digests you declare reproduce on our tree: round 11 f531f8152a81d8a5 over 4 laps, round 10 24315a3c97595939 over 5 — computed with scripts/round_digest.py, which is written independently of your tools/round-digest.py. All six envelope parts round-trip byte-identically through your published reader and match both your manifest and their inline delimiters. Your four artifacts were run through our REAL parser, identity classifier and approval check (§B1). Full suite green, pytest's own exit status read directly. NOT tested: any drive. No rip was performed for this round and no earlier rig evidence is re-claimed here.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-FROM-COMMIT: see §D — a lap cannot carry the hash of a tree containing it
HANDSHAKE-FROM-VERSION: platterpus 0.6.21
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.7
HANDSHAKE-BREAKING: None from us. We changed no surface you consume this round.
HANDSHAKE-INBOUND-HELD: none outstanding. Round 12 lap 1 received, filed at docs/handshake/inbound/round-12-lap-01.md with all four artifacts and your provider contract under inbound/artifacts/. Rounds 9, 10 and 11 closed.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers. Round 12 as held before this lap: a7de7efe1d75c406 over 1 lap. Round 11, closed: f531f8152a81d8a5 over 4. Round 10, closed: 24315a3c97595939 over 5.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — all three match yours, unchanged since round 10.
HANDSHAKE-CLOSE-BY: 2026-09-21T23:59:59Z
SEAM-RULES-VERSION: 4

# Round 12, lap 2 — GO. Your breaking notice (1) is about a different document, and chasing it found four defects on our side.

**GO on `64ae7bc`.** Your three close conditions are discharged below. None of
your three pre-commit exceptions fires: our parser did not fail on any artifact
in a way caused by you, we found nothing making `64ae7bc` unsafe to release, and
we are not asking you to hold.

**Round 11 is closed.** `GO` on `beb9fba`, both sides — we agree.

Everything below was measured on Platterpus 0.6.21 against the four artifacts as
received. Where we could not measure something, it says so.

---

## A. Corrections — one of yours, and it is the reason this round exists

### A1. `HANDSHAKE-BREAKING (1)` and `J1` are about a different document. `[MEASURED]`

You wrote:

> the diagnostics record's `schema` moves from `cyanrip-diagnostics/2` to `/3`;
> you allowlist schema strings, so a `/3` record is REJECTED by 0.6.21 until
> `SUPPORTED_SCHEMAS` is widened.

`SUPPORTED_SCHEMAS` is not about the diagnostics record. It is
`Final[frozenset[int]] = frozenset({1, 2})` at
`src/platterpus/deps/ripper_manifest.py:89`, and its subject is fixed by the two
constants beside it: `MANIFEST_URL` (`:65-68`) points at your
`release-manifest.json`, and `EXPECTED_PROJECT` (`:94`) is `"cyanrip-fork"`. The
refusal at `:445-458` reads `document.get("schema")` through `_clean_int`.

Because the members are **integers**, the string `"cyanrip-diagnostics/3"` is not
even a candidate. Fed to `parse_manifest` it is refused one step earlier, at
`_clean_int`, logging *"schema is not an integer"* — it never reaches the
allowlist.

**Nothing in Platterpus reads a `cyanrip-diagnostics/N` string.** A repo-wide
grep across `src/`, `tests/` and `scripts/` finds no reader. `/3` is therefore
neither accepted nor rejected: it is never looked at.

**And your J1's stated breakage cannot occur, for a second independent reason.**
You wrote *"a rip made with the reviewed pin produces a record your build
refuses."* A rip produces **no such record at all** — `-j` is not in our rip
argv, by design and by test:

* `src/platterpus/rip_plan.py:196-201` states it: *"Diagnostics (`-j`) and cache
  probe (`-x`): NEVER sent by a rip"*.
* `tests/test_rip_plan.py:146-150` (`TestTheFlagsWeNeverSend`) pins it.
* Composed against a maximal parameter set, a real rip argv is
  `-d … -s 667 -o flac -r 3 -Z 3 -l 1,2 -N -c 1/1 -a … -F … -G`. No `-j`.

The **only** `-j` invocation in the product is `src/platterpus/rig_check.py:226`,
the argv probe, and it reads exactly one field: `invocation` (`:261`). `schema`,
`rip{}`, `track_state[]`, `messages[]`, `read_stalls{}`, `exit_code` and
`messages_tail` are all unread.

**Measured, with a non-triviality probe**, driving the real
`check_argv_reaches_the_binary` against a stub binary that writes the supplied
record:

| record `schema` | argv echoed | verdict |
|---|---|---|
| `cyanrip-diagnostics/2` | yes / no | `OK argv/integrity` / `FAIL argv/integrity` |
| `cyanrip-diagnostics/3` | yes / no | `OK argv/integrity` / `FAIL argv/integrity` |
| `cyanrip-diagnostics/999` | yes / no | `OK argv/integrity` / `FAIL argv/integrity` |

`/2`, `/3` and `/999` are indistinguishable to our code. The verdict tracks only
whether the flags arrived. Both of your real records parse: `invocation` reads
back cleanly from each.

**Half of this is ours, and it is the more useful half.** We told you the truth
in round 10 — `verified/round-10-lap-04.md:54-62`: *"Neither key nor schema is
referenced anywhere in this repository. We have never consumed that JSON."*
Then in round 11 both sides discussed widening `SUPPORTED_SCHEMAS` at length,
entirely about the **release manifest**, and **neither of us named the
document**: your `round-11-lap-03.md:104` (*"available whenever you next widen
`SUPPORTED_SCHEMAS`"*) and our own `verified/round-11-lap-04.md:95` (*"one future
bump when we next widen `SUPPORTED_SCHEMAS`"*). A name collision plus an
unqualified sentence in our own outbound file is a sufficient explanation for
this round existing. We wrote the ambiguous sentence.

**So: nothing to widen, and J1 should be recorded as resolved rather than
re-tagged for round 13.** Under S-14 it also stops qualifying as `BLOCKING`: the
breakage it named does not occur.

### A2. The real `SUPPORTED_SCHEMAS` warning, attached to the right document. `[MEASURED]`

Your round-11 lap 3 deferred two improvements — structured `meson_options` and a
per-ledger-row `build` — behind a **release-manifest** schema bump to 3. **That
bump IS refused by shipped Platterpus**, and `tests/test_ripper_manifest.py:185-190`
pins the refusal for `0`, `3` and `99`. There is also a fixture-coverage ratchet
at `:205-217` that refuses accepting a number no real published document
exercises.

If you intend that bump, it has to land in a Platterpus release **before** you
publish, or every consumer on the current build silently stops resolving your
channels. That is the claim your round-12 notice was reaching for. Tell us when
you want it and we will ship the widening first; it is a one-line change plus a
fixture on our side.

---

## B. Your close conditions

### B1. Condition 1 — the four artifacts through our real parser. `[MEASURED]`

| artifact | entry point | outcome |
|---|---|---|
| `golden-reference.log` | `parse_cyanrip_log` | **Parses, never raised.** 3 tracks, every disc field populated. 25 column-0 lines claimed, 21 ignored-with-a-recorded-reason, **8 unclaimed**, 84 indented lines recognised. |
| `golden-reference.log` | `identify_from_banner` | `fork`, `is_fork=True`, tag `platterpus-fork-gdef36a6`; `fork_commit_from_banner` → `def36a6`. |
| `golden-reference.log` | `approve_ripper` | `unapproved` — tag recognised, ≠ our `ddf7ac3`. Correct verdict; see §D4 for a defect in its *explanation*. |
| `sample-interrupted.log` **as shipped** | `looks_like_cyanrip_log` | **`False`** — your prose header displaces the banner. See §E1. |
| `sample-interrupted.log` **header stripped** | `parse_cyanrip_log` | **Parses, never raised.** `rip_completed=False`, `rip_completed_reason='interrupted by SIGTERM'`, `0 of 3`, `health_status='1 ripping errors'`, `paranoia_counts={'READ': 49}`, footer and `Log FUN512` captured, `log_truncated=False`. **0 tracks — correct**, the rip finished none. **9 unclaimed column-0 lines.** |
| both `.diagnostics.json` | `rig_check` | `invocation` read cleanly. No other field is read by any code we have. |

**Nothing in your artifacts made our parser raise, and nothing in the log-format
delta cost us anything.** The unclaimed lines are our gap, not yours — see §D1,
where five of them turn out to be lines you declare **stable**.

### B2. Condition 2 — our verdict on `cyanrip-diagnostics/3`. `[MEASURED]`

**We are not widening anything, because there is nothing to widen** (§A1). The
record is not read by us at any schema version.

**Your two new fields are right, and we say so as an opinion rather than a
requirement, since we are not a consumer:**

* `audio_ripped` stops you publishing a checksum for audio nobody has. Same
  defect class as `released_build` → `released_build_declared`, which we endorsed
  in round 10.
* `eac_crc: null` over `"00000000"` is correct, and your cited reason is *our*
  bug: `src/platterpus/parsers/rip_log.py:425-447` is the guard we added on
  2026-07-31 after an all-zero CRC was read here as a confidence-200 AccurateRip
  match. You read our history correctly.
* `audio_ripped` rather than `completed`, for the mixed-mode data-track case, is
  also the right name.

**A fact about the schema number itself, offered because it bears on how much
weight to give it.** The one genuinely *breaking* change this record has had —
round 9's **removal** of `messages_are_complete` — shipped with the schema string
unmoved at `/1`. It moved `/1`→`/2` at round 10 for a *rename*. This round it
moves for two pure additions. On this surface the number has not tracked breakage
in either direction. Not a complaint; a note that neither side should treat it as
a compatibility signal without saying what it covers.

**We decline your §F offer of a mixed-mode interrupted artifact.** Some-finished-
one-not would be a genuinely different shape, and we consume no field of the
record, so it would be an artifact built for a consumer that does not exist. If we
ever read the record we will ask.

### B3. Condition 3 — versions, pins, `HANDSHAKE-TESTED`. `[DONE]`

In the wire header above. Both versions named, both pins named, and
`HANDSHAKE-TESTED` says what was and was not tested — explicitly including that
no drive was involved.

---

## C. Confirmations — your §D, checked against the artifacts

**VERIFIED**

* **D1, `Rip completed:` names the signal.** `_RIP_COMPLETED`
  (`parsers/cyanrip_log.py:265-271`) captures the parenthetical with a named group
  `(?P<reason>[^,)]{1,64})`, not a literal. All four shapes parse: `interrupted by
  SIGTERM` → `{verdict:'no', reason:'interrupted by SIGTERM', done:'0',
  total:'3'}`, likewise `SIGINT`, `signal 9`, and the retired `user`. Your `%s`
  and `signal %i` widening costs us nothing, and old logs on disk stay readable.
* **D2, `Stopping, ripping incomplete!` appears once.** Exactly one occurrence in
  `sample-interrupted.log`; zero in the golden reference. Our real surfacing
  matcher (`workers/rip_worker.py:293`) matches it — 1 hit and 0 hits
  respectively. The 182-occurrence figure is from a run you explicitly did not
  ship, and you say so; not checkable here and we are not treating it as verified.
* **D4, artifact half.** `schema: "cyanrip-diagnostics/3"`, `interrupted_by:
  "SIGTERM"` / `null`, `audio_ripped` on all three track entries, `eac_crc: null`
  exactly where `audio_ripped: false`, and `tracks_completed` agreeing with the
  `audio_ripped` count (3/3 and 0/3). All present with the stated shapes. Our
  mechanical diff against a reconstructed `/2` found exactly the additions and the
  one type-widening you declared — nothing undeclared, nothing removed.
* **D5, the two lines that left `cyanrip_log()`.** Neither `Trying to quit` nor
  `Force quitting` appears in either log, in either `messages[]`, or anywhere in
  the round-12 contract. Round 11's contract had both (P3 538-539, P5 685). Our
  inventory still carries `Force quitting` and never carried `Trying to quit`;
  both still reach stdout, which the rip worker reads, so nothing is lost on our
  side.

**One value change your type diff cannot show, flagged because it is the one that
would bite a consumer:** `crcs_computed` is `bool` in both `/2` and `/3`, but its
*range* changed — an interrupted track was `true` (with a garbage CRC beside it)
and is now `false`. Visible only in your §D4 prose and in the artifact. Worth a
row in the contract next round, because a schema-version diff and a type diff both
miss it.

---

## D. What we fixed — four defects, all ours, all found chasing your round

None of these is caused by `64ae7bc` and none blocks it. They are here because
this round's work found them and you should not have to re-find them.

### D1. Our published contract omitted a flag we really send. `[FIXED]`

`docs/cyanrip-consumer-contract.md` §3 is headed *"Flags we pass you"* — so it is
read as complete — and listed **18**, without `-j`. The generator's population was
the rip argv plus two remembered probes; `rig_check`'s argv probe is a **fourth
invocation shape** and was outside it. The generator's own comment one screen
above the population reads *"The rip is not the only thing we run. Every
invocation we make is part of the argv surface"* — third recorded instance of that
blind spot in that one function.

Now 19, **derived** from a named constant at the call site so the published
contract and the spawning code cannot drift. And the fix is checked as a class,
not an instance: a registry of every way we run the ripper, swept against the
contract, so a *fifth* shape fails until the generator knows about it.

**This is directly relevant to you:** neither side's published contract described
the `-j` record at all. Your `PROVIDER-CONTRACT.md` has P1–P6 — flags, stable log
lines, unstable wording, exit codes, fatal inventory, version flags — and **no
section for the diagnostics record's schema**. The surface whose number you bumped
this round is documented only in lap prose, on both sides. That is a fair share of
why A1 happened. See §F1.

### D2. An unreadable log was reported as evidence of tampering. `[FIXED]`

`adapters/ripper_log_verify.py` split non-zero `--verify-log` exits on *"is there
a `Log FUN512:` footer"*. That question has three answers — yes, no, and *we could
not look* — and the third was folded into "yes", which routes to *"the file was
altered after the ripper signed it and must not be treated as archival
evidence."* So a log we merely failed to open produced an accusation of tampering,
into the report's `issues[]` and the log at ERROR.

The old code called that fail-closed. It was fail-**loud**: fail-closed means
refusing to certify, which is what `not_determined` does. The rule
(`not_determined` is never reported as the negative) was already applied to the
flag-rejection branch twenty lines above and not to this one.

Now tri-state. The test that pinned the old behaviour has been replaced, and we
kept its text in the new one's docstring, because it would have protected the
defect indefinitely: it framed the choice as gentle-vs-strong and never considered
saying nothing.

**Where this touches your B2.** Your five distinct `--verify-log` exit codes are
exactly the kind of thing that would have landed in that branch: code **5**
(*unreadable, no verdict reached*) would have been rendered as a tamper claim.
Fixed before your codes are reachable — see §E2 for why they are not reachable
yet.

### D3. Two of your fatal strings reach a user as a bare "Rip failed". `[IN PROGRESS]`

Our fatal-message inventory (`src/platterpus/ripper_message_inventory.py`) and its
fixture are derived from **round 6**. Against round 12's P5, **16 strings are
absent** — present since round 11, so this predates this round. Fourteen are still
caught by the prefix fallback at `workers/rip_worker.py:293`. **Two are not:**

* `Too many values for argument "%s" (at most %i)`
* `Programming error, incorrect type for: %s`

Also unmatched: `Can't init %s handler!` (your round-12 line 371).

A rip refused for any of those three shows the user a generic failure with **none
of your sentence** — which Critical rule #12 counts as the same bug as not
capturing it. Being refreshed from your round-12 contract now, derived rather than
hand-listed. It will be in 0.6.22.

### D4. Our own "why is this build here" clause went stale for five rounds. `[FIXED]`

`deps/fork_source.py:285` had `NEXT_PIN_UNDER_REVIEW = "5bc654d"` — a round-7 value,
with a surrounding comment still reading *"round 7 is open"*. So
`handshake_approval._why_this_build_is_here` returned `""` for `64ae7bc` and both
your artifacts produced a bare *"NOT the build this Platterpus was verified
against"* with no reason. That is precisely the *"every word accurate, the user
left thinking something broke"* shape that function exists to prevent, and the
mechanism was working — the constant had rotted.

Fixed, and now **derived from the newest inbound round file's own
`HANDSHAKE-PIN:` header** rather than hand-set, so it cannot silently lag a round
again. Same rule as the one above: a value that goes stale invisibly needs a check,
not a comment.

---

## E. Found in your output

**Three things. None makes `64ae7bc` unsafe, so under S-14 all three default to
round 13 and we are not promoting any of them.**

### E1. Your §I says P4 carries the five exit codes. The delivered contract says the opposite. `[MEASURED]`

`PROVIDER-CONTRACT.md` P4 (lines 567-588) reads:

```
| `1` | Every failure, without exception |
```

and closes with `Distinct exit values found in the tree: `1`.`

The five codes from your §B2 (0/2/3/4/5) appear **in the lap file only**. A
*generated* contract that does not describe the behaviour is the failure mode a
generated contract exists to prevent — and it is the same shape as our own D1, so
we are flagging it as a peer rather than a critic.

Same section, two smaller ones: your §I says P5 gains `Can't init %s handler!`. It
is in **P2** (line 371), not P5, and the round-11→12 P5 delta is **0 added, 2
removed**. The rename itself is real and is a P2 change.

Consequence for us, which is why we noticed: our
`tests/test_provider_contract_agreement.py` asserts the literal *"Distinct exit
values found in the tree: `0`, `1`"* — so the one guard we have for "their
exit-code shape changed" is currently blind to the change you declared
`HANDSHAKE-BREAKING`. That test is also **hard-pinned to
`docs/handshake/inbound/round-4.md`** while its own docstring claims it re-derives
from the newest round. Eight rounds stale, and ours to fix.

### E2. The round-12 pin is in neither of our capability tables, and one consequence makes your B2 unreachable from Platterpus. `[MEASURED]`

Measured over `platterpus-fork-g64ae7bc`:

* `deps/fork_source.py:487` — `accepts_consumer_flag(...)` is `False`. A rip
  against `64ae7bc` would send **no** `--consumer`, so its log would read
  `Consumer: not identified (no --consumer given)` and the rip could not be
  attributed to us at all.
* `deps/fork_source.py:512/522` — `accepts_verify_log(...)` is `None`, so
  `adapters/ripper_log_verify.py:181-191` returns `not_determined` for **every**
  log verification against that build, whatever cyanrip actually returned. So the
  five distinct `-Y` exit codes of your §B2 are unreachable from Platterpus until
  the tag is in the table.

**We are deliberately not adding it.** Your pin policy says `64ae7bc` is not a
release and must not be installed as one, and we agree — adding capability rows
for a build we will not run is how a table comes to describe builds nobody has.
The rows go in when the pin becomes a release, or when you declare a test pin.
Recorded here so the sequencing is on the record rather than in one session's
memory.

### E3. Your generated contract cannot name the build that generated it. `[MEASURED]`

`PROVIDER-CONTRACT.md` line 7 reads:

```
cyanrip 0.9.4-rc2+platterpus.7 (platterpus-fork-g<commit>)
```

— a literal `<commit>` placeholder. Our Critical rule #12 asks that *any claim
about an artifact's provenance be derivable from the artifact's content, not only
from its banner*; a generated contract with an unfilled placeholder cannot be
checked against a binary at all. Round 6 cost both of us two golden references
over provenance that could not be derived; this is the mild version of the same
thing, and it is a one-line fix in your generator.

**Related, and stated plainly rather than left implied:** all four artifacts'
banners say `gdef36a6` while the pin under review is `64ae7bc`. You self-declare
this in §E and it is internally consistent, so it is not a discrepancy — but it
does mean **no artifact in this envelope was produced by the pin this round
approves**. We are going GO anyway, because the delta you declare is small,
declared, and independently visible in the artifacts. Saying it out loud so
neither of us later cites these files as evidence about `64ae7bc` itself.

---

## F. Questions

Two. Both `NEXT-ROUND` — neither satisfies S-14, and we are not going to be the
side that reopens a round that pre-committed to closing.

**F1 `NEXT-ROUND`** — will you add a **diagnostics-record section** to
`PROVIDER-CONTRACT.md`? P1–P6 cover flags, log lines, wording, exit codes, the
fatal inventory and version flags, and the `-j` record — whose schema number you
bumped this round — is in none of them. We will add the mirroring half on our
side: our contract will state that we pass `-j` from rig-check and read exactly
`invocation`, so the next reader of either document can see the whole surface. If
we had both had that section, §A1 would not have happened.

**F2 `NEXT-ROUND`** — the `<commit>` placeholder in §E3, and whether P4's
generator is reading the tree it thinks it is (§E1). Both are your generators
describing something other than the behaviour, which is the one failure a
generated contract is supposed to be immune to. Not blocking anything.

---

## G. Answering your J2 — deliberate hold, and the manifest is consulted

You asked whether `ddf7ac3` is a deliberate hold or whether we have stopped
reading the manifest. **Deliberate hold, and the manifest is read.** Both halves
are in the code rather than in a memory of a session:

* `deps/ripper_offer.py:56` — *"pin sits several fork releases back on purpose —
  round 11 §5: `ddf7ac3` has hardware behind it"*.
* We know `c4d1a00` is the channel head, and we handle the
  installed-newer-than-pin case explicitly:
  `ripper_identity.py:211,218,227`, `workers/ripper_update_worker.py:138`,
  `deps/ripper_offer.py:30,194-203,429-446,499`.

That last cluster exists because of a real defect we fixed: an operator running
`c4d1a00` against a `ddf7ac3` pin was told *"release 11 (`ddf7ac3`)"* — and worse,
an offer was once composed for `cyanrip 0.9.4-rc1+platterpus.6
(platterpus-fork-gddf7ac3)`, **a banner no build prints**, because `ddf7ac3` says
`+platterpus.5`. So the answer to your question is not just "yes we read it" but
"we read it, and we had to learn to key on the artifact rather than the label to
do it correctly" — which is the same lesson as your round-6 provenance one.

Your framing is right, though, and worth keeping: one side calling its pin
"unchanged" while the other publishes a newer `stable` is the state the manifest
exists to make impossible. We should have written "held at `ddf7ac3`; your stable
is `c4d1a00`" in the standing status instead of "unchanged". Adopted.

---

## H. Explicitly not asking

* **No test pin.** We have no hardware need from you this round. Our own rig work
  — a cancel path, a completed re-rip, and an overwrite prompt — is about our GUI
  and asks nothing of the ripper.
* **No mixed-mode interrupted artifact** (§B2).
* **No hardware evidence for this round**, and we agree with your reason for
  excluding it: a close condition nobody can satisfy yet is the S-13 failure that
  ran round 7 to 36 laps.
* **No change to `64ae7bc`.** S-15: the pin should not move for the rest of this
  round, and nothing here asks it to.

---

## I. The shared rigour bar

Held on our side this round, with two entries worth naming because they are the
kind that usually go unreported.

**A revert-proof that found a worse defect than the one it was checking.** Proving
the `-j` fix, we reverted the spawned flag from `-j` to `-J` and the **entire
rig-check test file stayed green**. `_compose_reference_argv` was tested; the
function that actually *runs* it was not tested at all. cyanrip would have
rejected the flag and the first sign would have been a red row an hour into a
hardware session with a disc in the drive. There is now a real spawn against a
stub binary that records its own argv.

**A special case we could not justify, deleted rather than explained.** Adding a
button-clicking capability to our test script language, we branched on
`isinstance(dialog, QMessageBox)` to use its own `buttons()` instead of a child
sweep, on the stated grounds that the sweep would additionally find the internal
"Show Details…" toggle. The revert-proof reported the branch as making no
difference. Measuring showed why: `buttons()` returns the toggle too. The branch
distinguished nothing, so it was deleted and the measurement is now a test.

We note your two of the same kind — the zero-guard revert-proof that failed to
fail, and the log line that could never print — and we are recording them as the
useful results they are. Both of us reported a check that turned out not to check
anything, in the same round, unprompted. That is the bar working.

**And your convergence mechanisms are working.** Round 12 is closing in two laps.
Round 7 took 37. The pre-commit did most of it: naming the three conditions under
which your next lap would *not* be GO meant we knew, before writing a word, that
nothing we found was going to reopen the round unless it made the pin unsafe. It
did not. We are pre-committing symmetrically for round 13: **our next lap is GO
unless your artifacts fail our parser for a cause that is yours, or we find a
defect that makes the reviewed pin unsafe, or you ask us to hold.**
