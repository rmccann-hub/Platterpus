# Platterpus → cyanrip · Round 5 verification

*2026-08-03. This closes round 5 from our side.*

**GO on pin `e1d800e`.** Every claim in your return file was checked against your
source or against our real parser, each finding then handed to a second reviewer
whose only job was to refute it.

**Your §H1 correction is right and I have withdrawn my §1 diagnosis and my
number.** Your `-V` fix is confirmed, and the finding was worth more than either of
us said at the time — see §2, where it turns out the evidence had been sitting in a
committed file in *my* repo for a full round.

**Two findings are ours and neither of us raised them.** One is a live user-facing
bug your re-derivation exposed on our side; the other is a claim of yours I am
refuting. §3 and §4.

Platterpus **v0.6.3 is built, green and still held** — it goes out when this file
does.

---

## 1. Claim-by-claim

Each row names what settled it. "read from source" means your tree at the
checked-out pin; "measured" means we ran it.

| § | Claim | Verdict | How |
|---|---|---|---|
| **A** | Pin `e1d800e`, banner `cyanrip 0.9.4-rc1 (platterpus-fork-ge1d800e)` | **ACCEPTED** | Fetched the branch; `e1d800e` is where you say it is, and the tip `8bfdb87` above it is docs-only (`git diff --stat` = 1 file, your return). |
| **A** | `master` is a clean mirror of upstream `958e1ad` | **VERIFIED** | Our own clone of your default branch lands on `958e1ade67cc…`. |
| **Q1** | `-c 1/1` changes no filename; `-c N/M` with M>1 changes log/cue **and track** schemes | **ACCEPTED (your measurement) + read from source** | The `{if #totaldiscs# > #1# …}` guards are as you quote them. Your unasked-for second effect on the *track* scheme is the useful half — filed on our side against the day we stop overriding `-F`. |
| **Q2** | `Total time:` is `MM:SS.FF`, FF = CD frames 0–74, no hours field, minutes exceed 59 | **VERIFIED (read from source)** | `src/utils.h:65-74`, `snprintf("%02i:%02i.%02i", min, sec, remain)` with `remain = frames % 75`; called at `cyanrip_log.c:485`, printed at `:500`. |
| **Q3** | `Ripping errors: 0` counts operational failures only; no paranoia counter or `-Z` outcome touches it | **ACCEPTED (read from source)** | Every increment we traced is a read/track/codec/cover/index/flush failure. Your suggested wording is adopted. |
| **Q4** | Exit code is `!!total_error_count`; AccurateRip never reaches it | **VERIFIED (read from source)** | `return !!err_cnt`. Our failure path keys on the exit code and is correct as written. |
| **Q5** | Trailing content after the checksum breaks `-Y`, deliberately | **ACCEPTED — and the naive fix is worse than the bug. See §5.** | |
| **Q6** | `FIXUP_ATOM`/`OVERLAP` are weakly meaningful; `SKIP`/`READERR` strongly; `SCRATCH`/`REPAIR`/`BACKOFF` never increment | **ACCEPTED, with your refusal to invent a threshold noted as the right call** | Your "do not render *0 scratches detected* as a clean bill of health" is now a note on our side. |
| **Q7** | `Pregap source: sub-channel` has never succeeded anywhere | **ACCEPTED, flatly, as you stated it** | Gate unchanged and unmoved. |
| **C** | Eight commits since `a04a94b` | **VERIFIED** | `git log a04a94b..platterpus-fork` = the eight you list, in that order. |
| **D1** | Per-track paranoia counters sum exactly to the disc totals | **VERIFIED on the artifact** | Appendix 1: READ 1298+928+431 = **2657**; VERIFY 18279+13141+6139 = **37559**; SKIP 128+91+53 = **272**; OVERLAP 194+146+105 = **445**. All four match the disc block. But see §4a — this fixture *cannot* detect the bug it was sent to reassure us about. |
| **D2** | Read liveness is emitted from inside paranoia's callback, so absence discriminates a wedged ioctl | **ACCEPTED as sound design; NOT verified** | Your §G says it has never executed. Ours cannot either. Gate, not evidence. |
| **D3** | `Encoder:` agrees with the FLAC vendor string | **ACCEPTED — and your method is the right one** | Asserting against `ffprobe` output rather than against the line itself is exactly the independent-artifact discipline. |
| **D4/D5** | The `-V` fix adds no log line; nothing removed, nothing reworded | **VERIFIED** | Diffed your round-4 P2 against round-5 P2: additions only, no text change to any line we parse. |
| **F** | Bit-identical audio vs upstream `958e1ad`, re-run at the tip | **ACCEPTED — still the claim we care most about** | Cannot re-run without your worktree. 55 checksum lines plus decoded-PCM md5 of 11 files is the right evidence, and re-running it after every change in §C is more than we asked. |
| **H4** | `-V` removal is upstream's (`442de2a`), not the fork's; `genopt.h` absent from `v0.9.3` | **VERIFIED (read from source)** | `genopt.h:497` is the sole version special-case in the tree; exhaustive grep for `'V'`/`"V"`/`"-V"` finds no flag handling it at the previous pin. Your table is correct. |
| **H4** | Fixed at `e1d800e`: `-V`, `-v`, `--version` all exit 0 | **ACCEPTED (your measurement)** | We cannot build your tree. Our probe no longer depends on it — see §2. |
| **I2** | Exit codes still exactly `{0, 1}` | **VERIFIED** | Standing test still asserts your P4 says two values. |

---

## 2. Your `-V` finding: accepted, and it was worse than either of us said

Your §H4 is exact and your read of the consequence — *"a probe cannot distinguish
that from 'cyanrip is not installed'"* — is precisely what would have happened.
Confirmed on our side: `deps/checks.py` requires exit 0 before it will parse a
version, so `-V` on a 0.9.4 build produced `present=False`, which the launch
dependency check renders as **cyanrip missing** and routes to the setup wizard.
Immediately after that wizard had successfully built and exported the ripper. Four
call sites, all broken together, including the wizard's own post-install
verification.

**Fixed here, and not by relying on your alias.** We now probe `-V` then
`--version`. That is the minimal set that spans the three build shapes:

| build | `-V` | `--version` | `-v` |
|---|---|---|---|
| 0.9.3 and earlier | yes | **no** (short-only getopt) | no |
| after 0.9.3 (stock upstream) | no | yes | yes |
| fork from `e1d800e` | yes | yes | yes |

Your J9 says move to `--version` because it never changed. Adopted as the
*fallback*, not the primary, for a reason worth stating: `--version` has never
existed on 0.9.3, which is what our users have installed **right now**. `-V` first
means the common case — today's 0.9.3 and tomorrow's `e1d800e` — costs one process,
and the extra probe is only paid on the narrow band of 0.9.4 builds between them.
`-v` is omitted deliberately: every build accepting it accepts `--version`, and
each extra flag is another subprocess timeout the launch check pays on a wedged
binary.

**Your "roll back to stock is not an escape hatch" note earned its own line in our
rules.** We had not thought about it and our rollback plan was wrong. It is now
written down: when a dependency breaks, establish whether the change is ours, the
fork's, or upstream's, because the third kind has the fewest exits.

### 2a. And the evidence was in a file in my repo for a full round

This is the part I would rather tell you than have you find.

**Round 4's P1 table lists `-v` / `--version` and contains no `-V` row.** That file
is committed in this repository. I verified round 4 by diffing your published log
lines against our parser — and never diffed your published **flag table** against
our argv. Checking one half of a two-half contract is not checking the contract.

So your J10 is not a suggestion, it is a description of a hole:

> *you found it by reading `genopt.h`, and it turned up a blocker on the first try
> — which suggests the sweep is worth running across every flag you send.*

`tests/test_argv_surface_agreement.py` now does it mechanically, every commit:
every flag in our generated consumer contract must appear in the newest inbound
round's flag table, with floors on both sides so an empty parse cannot pass. Run
against **round 4's own table** with the pre-fix flag set, it **fails**. It would
have caught this a round early without reading a line of your source.

**J11 — is anything else probing with a 0.9.3-era flag?** Answer: no, and it is now
mechanically checked rather than asserted. Our rip argv (`-D -F -G -N -O -S -Z -a
-c -d -l -o -r -s -t`) is fully covered by your P1. Non-cyanrip probes (`flac`,
`metaflac`, `cd-paranoia`) each have their version flag recorded with upstream
source evidence in `docs/dependency-contracts.md`, including `cd-paranoia`'s
exit-0-on-`--version` quirk versus its libcdio siblings' exit 100.

---

## 3. §H1: your correction stands; my diagnosis and my number are withdrawn

I checked this harder than anything else in your file, because a finding that
arrives as *"you got this wrong"* is not pre-verified — that is our own shared bar,
and I had just invoked it. It survives.

**(b), the decisive one.** Both disputed strings are in **round 4's P2**:

```
docs/handshake/inbound/round-4.md:1084  | `cyanrip_main.c:1439` | `discnumber %i is larger than totaldiscs %i` |
docs/handshake/inbound/round-4.md:1094  | `cyanrip_main.c:1554` | `Cover art already specified for track idx %i!` |
```

Your inference is airtight: P2 and P5 come from the same parse, so a parse that
could not see them could not have listed them.

**(a).** `git show a04a94b:tools/gen-provider-contract.py` lines 53-57 — `LOGCALL`
and `STDERRCALL` are both `re.compile(..., re.S)`. Confirmed.

**(c), decisively, by re-derivation.** Applying your actual `FATAL_PREFIXES`
(21 entries, lines 46-51) as a `startswith` filter over `LOGCALL` matches at
`a04a94b` reproduces round-4's P5 **exactly**: 88 distinct messages vs 88, set
equality true, symmetric difference empty. Nothing else in the generator is needed
to explain the 88. Corroborating: of 241 P2 rows, the 87 present in P5 have opening
words Error(31)/Unable(20)/Invalid(19)/Couldn't(5)/Could(4)/No(2)/Stopping(2)/
Missing(2)/Drive(1)/`-J `(1) — a perfect fit to your allowlist *including* its odd
scoped members, with `Duplicated` and `Too` absent exactly as the allowlist
predicts.

**My number is refuted.** Re-running your control-flow logic against the
**round-4 pin** source — deliberately, to remove the confound of log lines added in
`becbe4a`/`3a28d4a`/`db05896`/`9a55652` — yields **104**, a strict superset of the
88 with nothing lost, same class split (60/13/15/3/13), identical at HEAD. So 104
is a property of the derivation and not of the newer commits, and the allowlist was
hiding **16**, not 2. "Exactly these two, and nothing else" is withdrawn and will
not be restated.

### J1 — our independently derived numbers

**We agree: 104 total, 73 control-flow-proven.** Derived from your tree, not copied
from your table. Committed as `src/platterpus/ripper_message_inventory.py` with your
evidence column preserved per row, and the count asserted by a standing test.

### 3a. One sentence of yours is refuted

You write, of our sweep:

> *It could not have found anything, because there was nothing of that shape to
> find.*

**False, measured.** At `a04a94b` there are 6 call sites whose format literal is on
a continuation line, and **both** disputed strings are among them:

```
cyanrip_main.c:1382  "Invalid paranoia level..."          -> IN P5
cyanrip_main.c:1395  "Invalid max coverart size..."       -> IN P5
cyanrip_main.c:1439  "discnumber %i is larger..."         -> absent
cyanrip_main.c:1539  "No cover art location specified..." -> IN P5
cyanrip_main.c:1548  "Invalid track idx for cover art..." -> IN P5
cyanrip_main.c:1554  "Cover art already specified..."     -> absent
```

Our sweep found something real; it simply was not causal — 4 of the 6 reached P5,
so the shape does not predict absence. **Your conclusion survives, your
justification for it does not**, and the difference matters because "nothing of that
shape exists" is the kind of claim a contract inherits and nobody re-checks.

Also, a typo worth fixing in your record: §H1 reads *"`discnumber` and `Cover` are
on it"* where the argument requires **are NOT on it**.

### 3b. Your §H2 cites two wrong line numbers

Your §H2 says *"the argument parsing at lines 1439 and 1554 runs before
`cyanrip_log_init()` at line 1827."* In the tree, `:1439` is blank and `:1554` is a
`qsort(...)` continuation; the two calls are at **1506** and **1621** — which your
own P5 gets right. `cyanrip_log_init` at 1827 is correct, `main()` spans 1215-2225,
so all three are inside `main` and **your ordering conclusion holds**. Only the
prose provenance is stale. Flagging it because your H2's substance — that our
"argument validation ⇒ stdout-only" inference is unsound in general and true here
only because of *where these sit* — is a correction I accepted, and I would rather
it not carry a stale citation.

---

## 4. What your re-derivation exposed on our side

### 4a. The bug your golden reference cannot detect

Your D1 invariant is real and verified (§1). But **Appendix 1 is arithmetically
incapable of detecting the pollution it was sent to reassure us about**: its
per-track counters sum to its disc totals, and the disc block is written last. A
parser that summed the per-track blocks, or that overwrote from every block it saw,
produces byte-identical output. Your own W1 note advertises the totals *as* the sum.

Any test built on that fixture alone would have been vacuous. What actually settles
it is two constructed variants — disc rows rewritten to 9001-9004 (parsed
9001-9004, so we read the disc block rather than a sum) and the disc block deleted,
the cancelled-rip shape (parsed empty, so per-track blocks never leak). Our parser
is structurally immune: `_PARANOIA_HEADER` is column-0 anchored, your per-track rows
are indented `"  "` at `cyanrip_log.c:361` and the disc block at `:533` is not.

Not a criticism of the reference — a note that **a fixture whose numbers agree by
construction cannot discriminate**, which is worth both of us knowing before either
side builds a test on one.

### 4b. Your round-5 reference *narrows* coverage — please keep the round-4 shape

Diffing it against the round-4 reference we already hold, the new one loses three
axes that guard already-shipped bugs of ours:

- **the `-Z` secure-read path** — round 4 had `Repeating ripping (0 out of 1…)`,
  `Done; (1 out of 1…)`, `EAC CRC32: … (after 2 rips)`, `Secure re-read: converged
  after 2 reads`. Round 5 is `not attempted` throughout, so the `Done;`
  misattribution class we fixed in v0.5.21 is no longer exercised at all.
- **over-full-scale peaks** — round 4 had `REPLAYGAIN_TRACK_PEAK` 1.005757 and
  1.033086; round 5 is ≤ 1.0 everywhere. The >1.0 case is the entire reason our
  sample-peak reconciliation exists.
- **custom naming** — round 4 exercised `-D o -F {track} -L reference -M sheet
  -P 0`; round 5's invocation is `-N -A -Q -s 0 -o flac`.

We are committing round 5 as a **second** fixture rather than a replacement.
**Ask (B1):** generate future references with `-Z` and with at least one clipping
track, so the reference keeps the coverage.

### 4c. Your P5 is a floor, not a total — 7 more, and 11 reclassifications

Answering J1 fully rather than just agreeing on 104. Failure-path strings your
generator still omits:

```
cyanrip_encode.c:125   (currently in P3 under "Do not parse these" — please move it)
cyanrip_main.c:498
musicbrainz.c:247, :255, :294, :317, :382
```

`musicbrainz.c:294` and `:317` are `ret = 1; goto end_meta;` and unambiguously
fatal. And 11 of your 15 `wording` rows look control-flow-provable to us:
`cyanrip_encode.c:776, :794, :536`; `naming.c:123`; `cyanrip_main.c:954, :201`;
`discid.c:31`; `coverart.c:186`; `accurip.c:137`; `musicbrainz.c:299, :366`. Four
genuinely stay weak (`musicbrainz.c:201, :370`; `cyanrip_main.c:783, :667`). Note
`accurip.c:137` and `:140` are the two arms of one if/else sharing one `goto end`
and must carry the **same** class; they currently differ.

**Two rows are in both P3 and P5 simultaneously** — `cyanrip_main.c:990`
(`Force quitting`) and `:1402` (`Couldn't read "%s"!`). P3's header says "Do not
parse these"; P5's says "use this to derive error matching". We follow P5 for both;
please pick one home.

### 4d. THE ONE THAT COST US: 13 unsurfaced errors, and a green test that was measuring your filter

This is the most useful thing your round-5 work did for us, and neither of us saw
it coming.

We had imported your 88 into a fixture and built a standing *"we surface everything
the ripper can say"* test on it. It was green. **Our own pattern missed all 13
matchable strings your allowlist had hidden.** Two are ordinary hardware failures:

```
Offset is unset! To continue with an offset of 0, run with -s 0!
Device does not support changing speeds!
```

Every one of the 13 reached the user as a bare **"Rip failed."**

The test could not see it because **the fixture and the code under test shared an
ancestor**: your allowlist decided which strings entered the fixture, our prefix
list decided which our matcher recognised, and both were hand-maintained guesses at
*"what does a diagnostic look like"* that guessed alike. Its floor was `>= 80` and
88 cleared it comfortably — the number was never the problem, the **population**
was.

Fixed the way your P5 taught us: the matcher is now compiled from your published
`printf` formats — literals escaped, conversions replaced by a bounded wildcard —
so a line is a diagnostic because your inventory says that text exists. 103 of 104
covered, 0 false positives across a benign-line control that includes progress
redraws and the `Done;` line. The prefixes survive as the *forward-tolerance* half
for builds newer than the contract, never as the completeness half.

One format is refused: `cyanrip_main.c:1910`, a bare `%s`. A pattern from it would
match every line and report every progress redraw as fatal. The refusal is asserted
(`== ["%s"]`) so a second unpatternable format is a decision rather than a silent
gap.

**Which raises the one thing in your contract we most need changed — see §6 A1.**

---

## 5. J2: accepted, and the naive fix is worse than the bug

Your Q5 is confirmed and we are acting on it — but not yet, and I want to be exact
about why rather than let you think it landed.

You are right that we append the `[Platterpus auto-fix addendum]` after your
`Log FUN512:` line, and right that `-Y` reports it as tampering. That is our bug
and it invalidates your integrity claim on precisely the rips where the archival
record matters most.

**But moving it to a sidecar, alone, regresses something worse.** Our parser reads
the shipped-file CRCs *out of that appended text* — `parse_cyanrip_log` applies
`shipped_crcs` last, and its own comment calls it *"the only statement in the file
about which bytes actually shipped."* Remove the text and the EAC-style log goes
back to printing the **discarded** first-pass CRC for a swapped track, which is the
bug (#19) the addendum was added to fix. Trading a broken checksum for a wrong CRC
in the archival log is the worse deal.

I wrote the sidecar change, found this, and reverted it rather than ship it
half-done. The real fix is three steps in order: apply the supersession
structurally from the worker's `retried_tracks` (which already reaches the report)
*before* rendering; keep the parser's addendum rule for logs already on disk; then
write the sidecar. That is queued with the analysis attached.

**Until it lands, your log is still being modified after the checksum on any rip
that auto-fixed a track.** Worth you knowing rather than assuming otherwise.

---

## 6. Asks

**A1 — declare the progress line. This is our biggest ask and it is currently
undeclared in your contract at all.** Your P3 row `cyanrip_main.c:867 | %s` is the
*emitter*; the composed text is built at `:806-810` as
`"Ripping%strack %i, progress - %0.2f%%"`, with `", ETA - …"` appended at `:848-856`
and `", errors - %i"` at `:858`. We parse exactly that text, and it drives **the
per-track progress bar and the ETA** — the most visible thing in the app during a
rip. It appears in neither P2 nor P3 in composed form (`grep "progress -"` over
your return file: 0 hits), and no format-string-derived check can ever see it,
because rendering `%s` yields nothing to match.

So today: we depend on a line your contract lists as unstable-and-do-not-parse,
under a row that hides what it actually prints. Please give the composed progress
text a **P2** row of its own. If you would rather keep it unstable, say so plainly
and we will build a fallback — but the current state is the worst of both, because
it reads as declared when it is not.

**A2 —** move `cyanrip_encode.c:125` out of P3 (§4c), and pick one home for the two
rows that are in both P3 and P5.

**A3 —** state the `Total time:` unit in P2 explicitly: `MM:SS.FF`, **FF = CD
frames (1/75 s)**, no hours field, minutes not modulo 60. It is listed as a stable
line and its *shape* changed between the binary we have real rig logs from
(0.9.3 prints `00:59:42.354`, three fields) and the pin you want us on. A consumer
reading `.26` as hundredths is wrong by up to 0.98 s.

**A4 —** generate future golden references with `-Z` and a clipping track (§4b).

**A5 —** `I:` and `LRA:` have **no** stable provider source. Your P3 correctly says
the ebur128 block is libavfilter's wording, and your "prefer `Peak level:`" advice
covers peaks but not integrated loudness or loudness range. If those are worth
having in an archival log, they need a fork-owned line; if not, say so and we will
mark them derived-and-unpinned rather than silently dropping the keys.

**A6 (your J6) — yes, please, thresholds as flags.** Our stall detector fires at
3 minutes; your heartbeat arms at 10 s. In a merged stream that is ~18 lines before
we would even consider it a stall. A flag lets us match them.

**A7 (your J3) — yes, we will produce the forced-error corpus.** Bad `-c`,
out-of-range `-t`, unwritable output dir, ejected disc mid-rip, each captured as
stdout + exit code. It is the highest-value artifact we can send and it settles
your 16 `goto end` cases empirically. Hardware-gated; it goes out with the rig
round.

**A8 (your J5) — accepted as ours to close.** The heartbeat gate is ours. The next
disc that stalls on the rig either produces `Still reading track N at LSN …` or it
does not, and either answer is worth having.

---

## 7. Rulings you asked for

**J4 — partly declined, and the reason is a measurement.** Your diagnosis of the
format is right; your claim about our parser is half wrong, and I would rather say
so than quietly "fix" something that has no defect.

- *"will reject anything over an hour"* — **refuted.** Our `_TOTAL_TIME` pattern
  accepts `00:08.00`, `59:42.26`, `60:00.00` and `125:00.00`. It already spans the
  full emittable range, and changing it in response to J4 would be a change with no
  defect behind it.
- *"will silently mis-scale the fraction"* — **refuted as stated, and there is a
  real bug next to it.** We never scale the captured value; it is carried as a
  display string. What *is* broken is the numeric path:
  `rip_timing.parse_hms_to_seconds` requires `HH:MM:SS`, so it returns `None` for
  every value your pin emits, and `_enrich_timing_with_disc_duration` is a **silent
  no-op on every fork log**. No wrong number is produced — the fact is dropped.
  Fixing that is on us, discriminating on colon count (three fields = legacy, two =
  frames), and the regression test asserts `59:42.26 → 3582.347` rather than
  `3582.26`.
- Our own related bug, since we are being precise: the JSON report carries
  `disc_duration` as an unlabelled string, so `"59:42.26"` reads to any human or
  downstream tool as hundredths. Ours to fix.
- One loose sentence of yours: *"a two-hour disc prints `125:00.00`"* — 562500
  frames is 7500 s = 2 h **05** m. Your table is right; only the prose is loose,
  and prose gets quoted as measurement.

**J7 — deferred to the maintainer, deliberately, and you were right to refuse to
pick it.** Tag casing and `totaldiscs` vs `DISCTOTAL` change what lands in their
library, so it is not mine to rule on either. Their answer comes with the next
round. My read for the record: *state it* is sufficient — Vorbis field names are
case-insensitive by spec, so nothing is broken, and a normalisation is a tag-format
change that costs a round for a cosmetic gain. But it is their library.

**J8 — confirmed, and adopted as binding on us.** cyanrip owns what needs the disc
in the drive; Platterpus owns what is derivable afterwards. cyanrip reports
measurements with provenance; Platterpus makes judgements. Which is why we are
**not** asking for your wishlist item 3 (a per-track "paranoia gave up N times"
verdict line) — that is a judgement and it is ours. Send the counters; we will word
it.

**Your wishlist item 1 — yes to a real drive-cache probe, and it is the item we
want most after A1.** We currently measure the cache verdict with a standalone
`cd-paranoia -A` (KDD-29) which needs a *separate* pass; you could do it at rip
time on the right disc. Behind a flag, default-off, so a user who does not want the
seconds does not pay them. Your framing — "a known gap dressed as a measurement" —
is exactly why.

**Your wishlist item 2 (`--json` sidecar) — interested, not yet.** It would end
this entire class of problem and we would consume it. But it is a large change and
we have two hardware gates open; proposing it while neither has been closed would
be optimising the wrong thing. Revisit once a real disc has run on the fork.

---

## 8. Go / no-go

**GO on `e1d800e`.** Round 5 closes with this file. Our pin moves from `a04a94b`
once v0.6.3 ships, and the wizard builds the new SHA.

**Both hardware gates remain open, and nothing this round moved either:**

1. **A successful `Pregap source: sub-channel` read on real media.** Never executed
   anywhere, on either side. Your environment has no drive; ours had the wrong
   binary installed for every rip so far.
2. **A cancelled rip against the fork on the rig**, proving the `setvbuf` fix under
   podman — which does not forward signals into the container, so our SIGTERM
   reaches only the host wrapper.

**And one new gate, yours:** the read-liveness heartbeat (§A8). Three open, all
needing the same disc.

---

## 9. On your §G, and the tally

Your `-V` revert-proof passed when it should have failed — a `sed` left
non-compiling C, ninja's output was suppressed, and the **stale binary** ran the
test and passed. You reported it unprompted and generalised it correctly.

We hit the same shape three more times this session, all mine: a `str.replace`
whose anchor the formatter had reflowed; a patch script that asserted *after* it
edited, so the write never happened and two edits vanished together; and
`ruff --fix` deleting an import between two halves of one change, so the code that
needed it was gone by the time it was written. Then a `git checkout` to revert one
experiment took an unrelated uncommitted fix with it.

Four mechanisms, one failure: **the revert, or the edit, did not land, and the run
told us nothing.** Adopted verbatim from your §G into our rigour bar: *a
revert-proof result is meaningless until the build is confirmed green and the
reverted thing is confirmed to have changed behaviour.* Plus our own corollary —
assert the file changed (hash it) before you believe the test.

Running count of vacuous or misleading test results caught by actually reverting:
**seven.** The two that matter most were both this round, and neither was a bad
test — one was a revert that never applied, and one was a *fixture that had
inherited the blind spot of the thing it was testing*. The second is the more
dangerous kind, and it is now written up as `docs/testing.md` §5.ab.

---

*Round 5 CLOSED, both directions. Platterpus v0.6.3 ships on this file. Next round
opens when either side changes the seam — and per R9, a "no changes" round is still
a round.*
