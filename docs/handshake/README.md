# Handshake correspondence with the cyanrip fork

Every file exchanged with the cyanrip fork, both directions, committed so the
record survives the session that produced it. The protocol itself is
[`../cyanrip-handshake.md`](../cyanrip-handshake.md); the tool that enforces it
is `scripts/handshake.py`.

```
outbound/round-NN-lap-LL.md   what Platterpus sent    (protocol §3)
inbound/round-NN-lap-LL.md    what the fork sent back (protocol §4)
verified/round-NN-lap-LL.md   our verification of it  (protocol §2, step 5)
```

## File naming — `round-NN-lap-LL.md`

**Both projects use this.** Agreed 2026-08-04 on a maintainer directive (*"agree on a
naming convention for the handshake files and both use it"*), proposed to the fork in
lap 17, and enforced on our side by `tests/test_handshake_file_naming.py`.

| rule | why |
|---|---|
| The name states the **round** and **lap** from the file's own wire header | The filename becomes a *second description* of a fact the header already declares — safe only because a test asserts the two agree |
| Zero-padded to **two** digits (`lap-09`, not `lap-9`) | So a human scanning the directory reads it in order. Nothing in the tooling sorts on the string — see *Ordering* below — but `lap-9` sorting after `lap-10` in `ls` is its own trap |
| **Direction comes from the directory**, never the name; `HANDSHAKE-FROM` must agree with it | One fact, one place |
| **No amendment letters.** An amendment is a new lap | A lap number is a fact both sides can state; "the next free letter" is a fact only the filer knows |
| Generate it with `handshake_filename(round, lap)` | Never hand-typed — a typed name is a third description |
| Artifacts: `round-NN-lap-LL-<kind>-g<build>.<ext>` | `<build>` is the commit the artifact's **own banner** asserts, not the commit a lap file names it by. Those differ (see below), and only the banner is derivable from the artifact's content |

**Why it changed.** The old scheme was `round-N` plus the next free letter, and the
letter encoded nothing:

* `inbound/round-7f.md` was **lap 12** while `verified/round-7f.md` was **lap 10** —
  the same suffix meant different laps depending on the directory;
* `inbound/round-7d.md` and `verified/round-7d.md` were *both* lap 7, by coincidence;
* filing a received file meant picking "the next free letter", and picking wrong
  **overwrote a previous lap**. That happened: lap 12 was copied over `round-7c.md`,
  which was lap 4, and had to be restored from git.

**A file that declares no lap is lap 1 of its round** — the fork's rule, adopted in
lap 19 after their lap 18 showed the two projects had picked different numbers (we had
0) for one convention. Theirs is more correct: a round's pre-lap-header file *is* that
round's first lap, and calling it lap 0 invents a lap that never existed.

So the sole no-lap file of a **lap-numbered round** takes `lap-01`, because that name
states a derivable fact. Two conditions keep the exemption from becoming a hole: the
name must claim lap **1** specifically, and it must be the round's **only** no-lap file
— which is why round 6's three amendment files keep their legacy names. A round "uses
laps" iff some file in it declares one; rounds 1–6 are grandfathered wholesale.

**An ambiguous `HANDSHAKE-LAP` (declared twice, different values) sorts LAST.** Also the
fork's rule, and it closed a real hole on our side rather than merely aligning us: we
used to fall back to the filename, so an ambiguous file sorted at its *named* lap, a
later valid file was read as the newest, and the ambiguity was never examined by the
gate. Sorting it last makes it the file the verdict is read from, at which point the
header check refuses it.

## Artifacts — `artifacts-round-NN/`

Rig artifacts and derived records for a round live in `artifacts-round-NN/`, named
`round-NN-lap-LL-<kind>-g<build>.<ext>` — `<build>` being the commit the artifact's **own
banner** asserts, never the one a lap file names it by. Round 7's holds the 2026-08-04 rig
rip (log, auto-fix addendum, cue, rendered EAC-compatible log, JSON report) plus
`rig-session-results-c5fb909.md`, the derived record that says which artifact settled which
claim.

**Text only, ever.** Critical rule #8: the per-track CRCs prove bit-perfection, so no audio
is committed even temporarily.

## Ordering — four rules, and they are the spec's, not ours

**Ordering is `handshake.sort_key` — `(round, lap, stem)` — and nothing else may spell
it.** "Which file is newer" was a plain stem sort in three places and all three were
wrong the moment the naming schemes mixed; one of the three decides `--status`.

**The naming convention is not complete without these.** A shared *format* with
unshared *ordering* is a format both sides can honour while reading it differently —
which is the state both projects were in for one lap without knowing, because a
difference that changes no observable behaviour today is invisible to every test either
side can write. Three of the four below were found by *comparing implementations*, not
by a failing test.

| rule | where it comes from | why |
|---|---|---|
| **1. Order on `(round, lap)` from the wire header, never the filename string** | protocol §3: *"by declared number, never by filename or mtime"* | The filename is a description; the header is the declaration. **Qualified:** the header begins at round 7 lap 2, so for a pre-v2 file the name is the only fact in existence. "Never the filename" means *never in preference to the header* |
| **2. A file that declares no `HANDSHAKE-LAP` is lap 1** | protocol §3: *"absent means lap 1"* | A round's pre-lap-header file **is** its first lap. Not 0, which invents one; not unknown, which would let it outrank real laps |
| **3. An ambiguous `HANDSHAKE-LAP` outranks every real lap** | the fork's lap 18 §B1 | Present-but-ambiguous must be *examined*, not hidden. It becomes the file the verdict is read from, and the header check then refuses it by name |
| **4. `stem` is the third component, as a tiebreak only** | ours; the fork's three rules do not mention it | Two files at one `(round, lap)` is a state the convention forbids and `--check` refuses, but a **non-total** key makes "the newest file" depend on directory iteration order — which decides a release gate differently on two machines |

**Rules 1 and 2 were ours to fix, and both were divergences from a spec we already
ship** (found in lap 21 by diffing the fork's stated rules against our code, at their
request): our sort key read the *name* for the round half while the lap half already
read the header, and a lap-less file fell back to the name rather than to lap 1. Neither
changed the order of any file either project has ever had — which is exactly why only a
comparison could find them. **A spec statement with no conformance row went
unimplemented for the whole life of the spec.**

**Two states are refused rather than ordered** (`handshake.ordering_blockers`, consulted
by `--status` and so by `--release-gate`), because in both the permissive reading is the
wrong one:

* **a v2 file with no `HANDSHAKE-LAP`** — §2 rule 4, an absent required field fails
  closed. Under rule 2 it would sort *oldest*, so a later `GO` could be read as a
  round's newest word while this file's `HOLD` sorted underneath it;
* **a file whose declared round is not the round it is filed under** — §3 and §8 row 10.
  Believe the name and a file disowns its own declaration; believe the header and a file
  votes in a round it says it is not in. So neither.

Grandfathering is **derived** — a file with no `HANDSHAKE-PROTOCOL` line predates the
header and neither refusal applies to it — rather than a list of round numbers, which
stops covering the files added after it was written.

**A golden reference has two commits** and both get named — *"generated by X, committed
at Y"* (the fork's lap 16 §C). The build that produced it is the parent of the commit
that checked it in, because a file cannot contain the hash of a build containing itself;
regenerating inside the change's own commit moves the mismatch rather than removing it.
The filename carries X.

A round is **CLOSED** only when all three files exist **and both sides declare
`GO`**. The verdict closes the round, not the file's existence, and **one side's GO
is not enough** — reading only our own verdict made the fork's `HOLD` unable to block
our release. `python scripts/handshake.py --status` reports both:

```
round-6: ... we-verified=yes (GO)   they-verified=yes (GO)    -> CLOSED
round-7: ... we-verified=yes (HOLD) they-verified=yes (HOLD)  -> OPEN
```

**No release and no pin switch happens while any round is OPEN.** See
`../cyanrip-handshake.md` §7.5 for why the gate reads the verdict at all (it used to
read presence, and reported a HOLD as closed) and **§8 for the shared wire format** —
the column-0 header block both projects now emit, after both built a release gate in
a different vocabulary and neither could read the other's files.

## Round-by-round

Newest first. `pin` is the fork commit the round concerns; the **live** pin is
whatever `src/platterpus/deps/fork_source.py` builds, which only ever moves to a
commit a *closed* round verified.

| Round | Pin | Verdict | What it was about |
|---|---|---|---|
| **8** | `ddf7ac3` (`0.9.4-rc1+platterpus.5`) — test pin `cb440bd` | **HOLD (ours, lap 8) — OPEN** | Opened by the fork with a **test pin**, which by their §6a cannot close a round and never moves `HANDSHAKE-PIN`. The round the correspondence stopped being a document: one joint **script**, ours in sections A/B/D, theirs in C, returned changed rather than commented on. Validating their returned SECTION C through the real parser found 3 of 6 ripper tests would be refused before the binary saw them — and **two of the three were ours**: we refused `--verify-log <path>` while our own adapter has sent exactly that argv, unaccompanied by `-N`, once per rip since v0.6.x; and nothing in our pipeline expanded `~`, so their `--verify-log ~/Music/…` test would have exited 1 on a path error and passed for the wrong reason. Both fixed in 0.6.12, along with a preflight that names every refusal before step 1 instead of forty minutes into a disc pass. Their §H found `platterpus --install-ripper <sha>` unusable on an AppImage — one instance; a sweep found seven. **Found against ourselves:** laps 3–7 were never committed, so `--status` could not see the round at all and four releases went out during it; `CURRENT_ROUND` is now a floor the gate counts even with no files. |
| **7** | `345241b` → `422d12a` (`0.9.4-rc1+platterpus.5-beta.8`) | GO both sides at lap 39 | Their §7 measured both rip sessions at 81m11s / 81m13s, refuting our "much faster" explanation — we had described the dynamic-rerip mechanism and let it stand as the cause of a delta never measured. Their §5 pre-gap `Duration:` off-by-one-frame reproduced on our rig, with a sign flip they had not reported (+1 on tracks 1–13, **−1 on track 14**). Their file shipped no §I provider contract; their lap 2 replaced the whole idea with a generated contract plus a resolvable pointer, which is better. Lap 3 adopted their header format as the shared wire format (§8), made the gate bilateral, and put a handshake-approval check in every rip. **41 laps, 10 test pins, 8 pre-releases, 0 releases** — the round that produced S-13…S-16, the convergence rules, because nothing in it was bad work and it still could not end. |
| **6** | `2f950c8` (fork release r2) | GO | The round that took three pins in one day. Their finding: at any paranoia level above 0, ripping a **disc image** returned one correct sector then silence — 99.7% of samples zeroed, reported as `Ripping errors: 0` — inherited from upstream, never affecting a real drive. Ours: two consecutive golden references whose build tags named commits three behind their content; per-track paranoia counters are per-**pass**, not per-track; their §C7 refuted by their own appendix. Amendments `6b` (urgent pin withdrawal) and `6c`. |
| **5** | `e1d800e` | GO | Found the release blocker: every version probe we shipped sent `cyanrip -V`, which upstream deleted after 0.9.3 — and a non-zero exit from a version probe reads here as *"the tool is not installed."* Also found our strongest-looking test was measuring **their** generator's allowlist, not the ripper: their fatal inventory went 88 → 104 on re-derivation and our matcher had missed all 13 matchable strings the allowlist hid. |
| **4** | `a04a94b` | GO | First round under `scripts/handshake.py`, and the round that added §I (the provider contract) to the spec. Their §B answers checked and their golden reference run through the real parser. |
| **3** | — | GO *(retrospective)* | The fork's return file, verbatim. Our verification was **late** and went out folded into round 4's outbound §1–§3 rather than as its own step-5 file — which `--status` is what surfaced, and is a fair summary of why the tooling was written. |
| **2** | — | GO *(retrospective)* | `setvbuf` as the fix for the buffering defect a signal handler cannot reach, and the `-l` track-selection semantics. |
| **1** | — | GO *(retrospective)* | The fork's FIXPLAN: cyanrip's logfile and cue are block-buffered, so a killed process loses up to a 4096-byte stdio block. Reproduced against a real cancelled rip whose log ended mid-token at `REPLAYGAIN_TRACK_GA`. |

Rounds 1–3 carry no `**GO`/`**HOLD` marker — the convention began at round 4 —
so they are grandfathered by number in `handshake.RETROSPECTIVE_ROUNDS`, a set a
test pins to exactly `{1, 2, 3}`.

## These files are correspondence, not documentation

They are deliberately exempt from the doc version-stamp convention
(`tests/test_doc_version_stamps.py`). Stamping an inbound file would edit
another project's words; stamping an outbound one would make the committed copy
differ from what they actually received. A record that is not the record is
worthless. Their currency is the round number.

Do not edit a file here after it has been sent or received. If something in it
was wrong, that belongs in the **next** round's Corrections section — which is
the mechanism, and most of the errors found so far arrived that way.

## Amendments

`round-6b.md` is **round 6**, not round 6b. A round may be amended — round 6 was,
within hours, because the pin it asked for returned silence on disc images —
and `handshake.py` reads `round-<N><suffix>.md` as round *N*. Counting an
amendment as its own round would report two open rounds where one was corrected,
and would make sending a correction immediately score *worse* in the record than
sitting on it. `--check` accepts several files so a round validates as a set, and
`--status` takes the **newest** file's verdict, so a GO withdrawn the same evening
does not keep a round closed.

## Backfill note

Rounds 1–3 predate `scripts/handshake.py` and were recovered from the session
scratchpad, so their section shapes vary and `--check` will report rounds 1–3
against the current spec. That is expected: the spec grew (§I, the provider
contract, was added in round 4). Round 3's `inbound` is the fork's file verbatim.
