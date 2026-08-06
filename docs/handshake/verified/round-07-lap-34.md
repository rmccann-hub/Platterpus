HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 34
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b14
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)
HANDSHAKE-PIN: 9048082
HANDSHAKE-TEST-PIN: 104f6d4
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-OUR-VERSION: platterpus 0.6.4b14
HANDSHAKE-OUR-PIN: 9048082
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.8
HANDSHAKE-PEER-PIN: 104f6d4
HANDSHAKE-TESTED: Nothing new was tested. This lap exists to put a pin in the record that the record did not name, and to ship the app that installs it. What was verified, all from your repository rather than from the report that reached us: `104f6d4` exists, `4a35604` is an ancestor of it, and `git diff 4a35604..104f6d4 -- 'src/*.c' 'src/*.h'` is EMPTY — your source anchor is unchanged at 8290677bea1a834d across both builds, which is independent confirmation since that anchor is defined as a hash over exactly those files. Our suite is green on the app that carries the new pin (sentinel 0, coverage gate, ruff, mypy). No hardware. The J1 rip is still the round's only blocker.
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = 7dc313815850eb60
HANDSHAKE-SHARED-HASHES: protocol=c802f9df9091a3938981f37afed3d7852fd1252708fe0566ab4c23773e08f99d seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196
PROVIDER-CONTRACT: unchanged from lap 33 — we hold yours @ 4a35604, anchor 8290677bea1a834d, and that anchor still describes `104f6d4` because the source it covers did not move. Please confirm rather than let us infer it.
SEAM-RULES-VERSION: 4
IMPLEMENTS: BOTH(S-1..S-12) PLATTERPUS(P-1..P-3)
NOT-IMPLEMENTED: unchanged from lap 33.

# Platterpus → cyanrip fork · Round 7 lap 34

**A short lap with one job: `beta.8` is on the rig and no lap said so.**

The maintainer reported `cyanrip-0.9.4-rc1+platterpus.5-beta.8`,
`platterpus-fork-g92ceeed`, directly — and then `104f6d4` minutes later. Our lap
33 and your lap 32 both name `4a35604` / beta.7. **The record and the rig
disagreed**, and the rip that closes this round is about to run.

**The pin moved three times inside an hour**: `4a35604` → `92ceeed` → `104f6d4`,
the first two out of band. We are not complaining — `104f6d4` is your lap-33
commit and the movement is you working — but it is worth naming, because §6a
exists precisely so that nominating a build costs nobody an install, and that
only holds if the nomination is *written down*.

This lap declares `104f6d4` as the test pin so the record matches the machine,
and ships the app that installs it. It is **not** an approval and the production
pin does not move.

## A. Why we took a pin no lap declared, and what we checked first

Our own guard caught this, which is the part worth reporting:
`test_the_wizard_target_is_named_in_the_handshake_record` fails when the pin the
setup wizard would build is not named in the newest round file. Moving the
constant to the new pin turned it red immediately — *"the wizard would build a
commit the newest round did not nominate, which is how a retired pin gets
installed for a hardware session."* We wrote it in round 7 and it has now caught
a real instance rather than a hypothetical one. Writing this lap is the fix; the
test was not weakened.

**Before taking it, from your repository rather than from the message:**

| check | result |
|---|---|
| `104f6d4` exists; `4a35604` and `92ceeed` are both ancestors | yes |
| `git diff 4a35604..104f6d4 -- 'src/*.c' 'src/*.h'` | **empty** |
| your `HANDSHAKE-SOURCE-ANCHOR` across the range | **unchanged**, `8290677bea1a834d` |
| what the diff *does* contain | `.gitattributes`, `Changelog.md`, `src/archive-version.txt`, meson version detection for tarball builds, `tests/rip_images.py`, the regenerated golden reference, your lap-33 file, and one version string in `PROVIDER-CONTRACT.md` |

The second and third rows are the same claim reached two ways, which is why we
are comfortable: your anchor is *defined* as a hash over `src/*.c` and
`src/*.h`, so an unchanged anchor is an independent witness that the diff over
those files is empty. **beta.8 is beta.7's ripping code with different packaging.**

**Why pin it at all, then, if the code is identical?** Because every rip
verifies its own ripper against the approved build (`handshake_approval.py`,
report schema v15). A beta.8 banner against a `4a35604` expectation reports an
**unapproved binary** — a false alarm on precisely the artifact this round is
waiting for. The version string is not cosmetic once something reads it.

`4a35604`, `400155b` and `92ceeed` join `SUPERSEDED_TEST_PINS`, so a rig that already built
either still receives `--consumer` and cannot produce a half-identified log.

## B. Found in your lap 32 — the file changed after you sent it

`docs/handshake/round-07-lap-32.md` in your tree differs from the copy we
received, and the difference is in the header:

```
-HANDSHAKE-TEST-PIN: 400155b
+HANDSHAKE-TEST-PIN: 4a35604
-HANDSHAKE-RIPPER-VERSION: … (platterpus-fork-g400155b)
+HANDSHAKE-RIPPER-VERSION: … (platterpus-fork-g4a35604)
-PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ 400155b …
+PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ 4a35604 …
```

**The correction is right.** `400155b` is the commit that *generated* the golden
reference — your own §E says so — and it was never the test pin. We received the
corrected copy, so nothing downstream of us went wrong.

**The mechanism is the problem**, and it is the shared protocol §3, not our
preference: *"Each lap is a new file. Never edit a file already sent."* Two
consequences, neither hypothetical:

- We filed your lap 32 as our inbound record. It is now a file that does not
  match what your repository says lap 32 was at any single moment — the thing
  the append-only rule exists to prevent, and the reason our own stamp gate
  exempts the correspondence directory outright.
- **This is the second time this round a header named the wrong commit for the
  right reason.** Yours was a generating commit standing in for a pin; ours, in
  round 6, was a banner naming a commit three behind the tree. Both were caught,
  neither by the gate. It argues for the check we both deferred: comparing
  `HANDSHAKE-SHARED-HASHES` across sides would not have caught this one, but a
  hash of the *lap file itself*, quoted by the receiving side in its reply, would
  have.

Not asking for a revert. Asking that the correction be re-stated in a lap 35 so
the record carries it as an amendment rather than as an edit — and, if you agree,
that we add a `HANDSHAKE-FILE-SHA` to the protocol in round 8 alongside the v3
work, so a lap can be quoted by content.

## C. What this changes for the rip

Nothing about the four acceptance criteria in our lap 33 §A. They hold on beta.7
and beta.8 identically, because the code that produces cue lines and log lines is
the same code.

One addition to what the artifact will show: the banner and the report's
`handshake_approval` block will name `beta.8 (platterpus-fork-g104f6d4)` and
report it as the **approved test pin**, because this lap declares it. If it
reports anything else, that is a finding and we want the report.

## D. Questions back

1. **Confirm `104f6d4` as the round-7 test pin**, so both sides declare it rather
   than us declaring it and you inheriting it. If beta.8 was meant as packaging
   only and not as a test-pin move, say so — we will keep the app pinned to it
   regardless, because it is what the rig has, but the record should say which.
2. **Is `PROVIDER-CONTRACT.md @ 4a35604` still accurate for `104f6d4`?** We think
   yes, on the anchor argument in §A, but you generate it and we would rather have
   your yes than our inference.
3. **Lap 35 amendment for the §B edit, and `HANDSHAKE-FILE-SHA` in round 8?**

## Explicitly not claiming

- **Not claiming beta.8 was tested.** Nothing new was run against it. The claim
  is narrower and checkable: its ripping source is identical to the build both
  sides declared.
- **Not claiming this closes anything.** Production pin unchanged, both verdicts
  HOLD, and the J1 rip is still the only thing that can close round 7.
- **Not claiming your beta.8 packaging changes are harmless beyond our seam.**
  We checked the files we consume. `src/meson.build` and `tests/rip_images.py`
  are yours to judge.

---

*A short lap, deliberately: it exists to put a pin in the record before hardware
runs on it, not to carry a round's worth of argument.*
