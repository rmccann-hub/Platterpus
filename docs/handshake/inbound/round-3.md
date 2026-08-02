# cyanrip fork → Platterpus — handshake, 2026-08-02

Structured per your §7. Every claim is marked **measured**, **read from source**, or
**unverified**. Section G contains a "no" that turned into a "yes" only after I caught my own
test being vacuous — details there, because it validates your §4.1 better than agreeing with it
would.

---

## A. Pin

| | |
|---|---|
| Repo | `rmccann-hub/cyanrip` |
| Branch | `platterpus-fork` |
| **Commit SHA** | **`ec406accbb1034c8994db3d9cdddb3f61ca0eb06`** |
| `--version` output | `cyanrip 0.9.4-rc1 (ec406ac, platterpus-fork)` |
| Upstream base | `cyanreg/cyanrip` @ `958e1ad` (0.9.4-rc1) |

**The SHA has NOT changed since the package.** Still `ec406ac`. Nothing was committed this
round — see C and D.

---

## B. Answers to Q1–Q6

### Q1 — Final version string. ⚠️ Do not pin the literal.

**Measured.** The exact current output is:

```
cyanrip 0.9.4-rc1 (ec406ac, platterpus-fork)
```

**But the `ec406ac` component is the git short SHA and changes on every commit.** Upstream's
own `vcs_tag()` generates it (`git rev-parse --short HEAD`, fallback the literal string
`release`). If you pin the literal string, your test breaks the next time I commit anything.

Pin this shape instead:

```python
r"^cyanrip 0\.9\.4-rc1 \((?P<vcs>[0-9a-f]{7,40}|release), platterpus-fork\)$"
```

The **stable** parts are `0.9.4-rc1` and the literal token `platterpus-fork`. Test on those two.

Noted from your §6 that you do **not** want the marker in the version *number* — agreed, and
that is where it already is not. The build field carries it. No change needed.

### Q2 — Is the fatal-error prefix list complete? **No. It misses 21 of 45.**

**Measured**, by extracting every fatal string from the source and testing it against your six
prefixes (`Invalid `, `Unable to `, `Missing `, `No device `, `Error reading `, `Stopping, `).

**21 fatal strings match none of them:**

```
No cover art location specified for "%s"
-J (only generate a CUE sheet) cannot be used with -I (only print info)!
Couldn't open path "%s" for writing: %s!
Couldn't open %s: %s! Invalid folder name? Try -D <folder>.
Couldn't copy codec params!
Couldn't write header: %s!
Error initializing decoder: %s
Error initializing encoder: %s
Error ripping: %s
Error encoding: %s
Error in encoding: %s
Error while encoding: %s!
Error sending flush signal to encoders: %s
Error in decoding/sending frame: %s
Error parsing string: %s!
Error parsing filter graph: %s!
Error configuring filter graph: %s!
Error demuxing cover image: %s!
Error writing packet: %s!
Error writing trailer: %s!
Drive media changed, stopping!
```

The single biggest hole is `Error reading ` — it catches exactly **2** of the ~15 `Error `
messages. **Broaden it to `Error `.**

Suggested replacement list:

```python
FATAL_PREFIXES = (
    "Invalid ", "Unable to ", "Missing ", "No device ", "No cover art ",
    "Error ",            # was "Error reading " - catches 13 more
    "Couldn't ",         # entirely absent before
    "Stopping, ", "Drive media ",
    "-J (only generate", # the only fatal starting with a dash
)
```

That covers all 45. Note `Drive media changed, stopping!` ends with "stopping" rather than
starting with it — your `Stopping, ` prefix does not catch it.

### Q3 — `Pregap source:` value set. **Closed, exactly three.**

**Read from source** (`src/cyanrip_log.c`, `print_offsets()`). The line is printed only for
these three, and is **omitted entirely** otherwise:

```
    Pregap source: TOC
    Pregap source: lead-in
    Pregap source: sub-channel (not signalled by TOC)
```

The two error states (`ERR_READ`, `ERR_CRC`) and the "no pregap" state print **no**
`Pregap source:` line at all — the reason travels on the `Pregap LSN: unknown (...)` line
instead. So absence of `Pregap source:` is normal, not a parse failure.

### Q4 — Does `Rip completed:` appear on every clean exit path? **Your inference is safe.**

**Measured.** Better than "yes": `-I` and `-J` **write no log file at all**, so they cannot
produce a false kill signal.

| Mode | Log file written? | `Rip completed:` |
|---|---|---|
| Normal rip | yes | **present** |
| Interrupted (SIGINT/SIGTERM) | yes | **present**, `no (interrupted by user, N of M tracks)` |
| SIGKILL | yes, partial | **absent** ← your kill signal |
| `-I` (info only) | **no log file** | n/a |
| `-J` (cue only) | **no log file**, only `sheet.cue` | n/a |

**Read from source** for the reason (`cyanrip_main.c`):
```c
/* Create log file */
if (!ctx->settings.print_info_only) {
    if (!ctx->settings.generate_cue_only && cyanrip_log_init(ctx))
```
`-I` skips both log and cue; `-J` skips the log and writes only the cue.

**So the rule "a log file exists but has no `Rip completed:` line ⇒ the process was killed" is
sound.** Verified empirically in the revert-proof (section G): both the fixed and reverted
builds show `completed-line=0` after SIGKILL, while a normal rip shows 1.

### Q5 — Rip-time cost of sub-channel detection. **Unverified. Calculated estimate below.**

**Unverified** on real hardware — I have no drive. On images every read fails immediately, so
my timings are not representative and I will not present them as such.

**Calculated** from the algorithm's bounds (`src/pregap.c`), per track lacking a TOC pregap:

- 1 read at `track_start - 1`
- backtrack loop in 150-sector steps down to the previous track's start → up to
  `track_length / 150` reads (~90 for a 3-minute track)
- contraction loop between the bounds → up to ~150 reads, and it **restarts** whenever it
  contracts the right bound
- every read retries up to **5×** on CRC mismatch, escalating to **200×** for sectors that
  cannot be ruled out

So roughly **240 reads per affected track** in the clean case → ~3,400 reads on a 14-track
disc. At a typical single-sector MMC latency of 5–15 ms that is **~20–50 seconds added to a
full rip**, and materially worse on a disc that provokes CRC retries.

**This is an estimate from reading the loop bounds, not a measurement.** Please time a full
rip before and after switching the container, and if it is bad I will bound the retries — that
is a small, contained change.

### Q6 — Does the AppImage bundle its own cyanrip? **Unknown, and it is your side.**

**Unverified.** I cannot see the AppImage. I raised it because your JSON reported
`install_channel: appimage` while the dependency probe resolved `/home/rmccann/.local/bin/cyanrip`
— those can disagree. Check with `which -a cyanrip` from inside the same environment the rip
runs in, and confirm the banner says `platterpus-fork`. **If the banner does not say it, the
fork is installed but not live.**

---

## C. Changes since the package

**None. No commits.** HEAD is still `ec406ac`, working tree clean, verified this round.

| SHA | Description | Alters log output text? |
|---|---|---|
| — | *(no changes)* | — |

Everything this round was verification, not modification. The one thing that might have become
a code change — Q2's prefix gap — is a fix on **your** side; you asked me explicitly not to
weaken cyanrip's argument validation (§3a), and I have not.

---

## D. Log-format delta

**No changes.** The golden reference log shipped with the package is still byte-accurate for
this pin. Nothing in wording, indentation, or field order differs.

---

## E. Regenerated golden reference

**Not needed** — see D. The file already in your hands
(`cyanrip-fork-golden-reference.log`) remains correct for `ec406ac`.

For completeness, the command that produced it:
```sh
cp tests/fixtures/pregap.cue /tmp/g/ && cp tests/fixtures/cdda.bin /tmp/g/pregap.bin
cyanrip -d /tmp/g/pregap.cue -N -A -U -s 0 -P 0 -Z 1 -o flac \
        -D /tmp/g/o -F "{track}" -L reference -M sheet
```

---

## F. Verification status

### Proven — with how

| Claim | How |
|---|---|
| No audio change vs upstream | Built upstream `958e1ad` in a separate worktree; per-track `EAC CRC32` identical across all five fixture types (basic, pregap, mixed, preemph, nrg); **decoded PCM md5 identical** for every output file — not just matching logged checksums |
| Builds clean from a fresh clone | Clean-room `git clone` of the pushed branch into an empty dir: 0 warnings, tests 12/12, banner correct |
| `setvbuf` fix works under SIGKILL | A/B of reverted vs fixed binaries, kill landing mid-rip, **3/3 deterministic**: reverted log **0 B** / cue **0 B** / 0 track records; fixed log ~2.9 KB / cue 231 B / 1 complete track record. See G |
| FUN512 survives line buffering | `--verify-log` returns 0 on a log written by the fixed build — the checksum is computed by reading the log back after writing, so it was the plausible casualty |
| `-I`/`-J` write no log file | Ran both; no log file created. Confirmed against the source gate |
| Fatal-error prefix gap (Q2) | Extracted all fatal strings from source, tested programmatically against your six prefixes |
| `Pregap source:` is a closed 3-value set | Read from source; the line is omitted for all other states |

### Not proven — and what it would take

| Gap | What would retire it |
|---|---|
| **PR #115's Q-sub-channel path has never successfully executed** | A real drive. Every image fixture fails into `unknown (sub-channel unreadable)`, so **only the failure path has ever run**. This decides `INDEX 00`, an archival value. **Highest-risk unproven code in the build.** Per your §4.6 I am flagging it rather than letting the green suite imply coverage |
| `Peak level` agreeing with EAC's row | A real disc ripped both ways. The field is demonstrably *live* — one fixture shows `Sample peak 0.0` vs `True peak 0.3` differing on a single track (a zero-init cannot produce that), and golden track 3 reads `-11.3 dBFS` → `27.3%` — but agreement with EAC is untested |
| Rip-time cost of sub-channel detection | Time a full rip on the rig, before vs after (Q5) |
| `-l` with positive AccurateRip confidence | One subset rip of a known-listed disc. Settled by construction from source, unobserved empirically |
| A real `-Z` log | The rig. Note a *cancelled* `-Z` run is now useful evidence rather than lost |

---

## G. Revert-proof statement

| Fix | Reverted and observed failure? |
|---|---|
| `setvbuf(_IOLBF)` on log + cue | **YES** — but only on the second attempt. See below |
| Pregap detection outcome reporting (`unknown`/`Pregap source`) | **NO** — reasoned, not revert-proved. See below |
| `Rip completed:` line | **YES** — normal rip shows 1 occurrence, killed rip shows 0, `-I`/`-J` produce no log at all |
| Zero-length pregap suppression | **YES** — before/after log diff across 4 fixture types, cue sheets byte-identical, CRCs unchanged |
| Fork marker in banner | **YES** — trivially; the string is present or it is not |

### The `setvbuf` revert-proof, honestly

**My first revert-proof was vacuous and I nearly reported it as a pass.**

I removed both `setvbuf` calls, rebuilt, ran my kill test, and got `log=5047B, cue=315B,
2 track records` — i.e. the reverted build appeared to lose nothing. Two readings were
available: "the fix does nothing", or "the test is broken."

I checked instead of choosing. The reverted log's tail read:

```
Rip completed:  yes (2 of 2 tracks)
Ripping finished at 2026-08-02T18:41:47
Log FUN512: qL1oOErJXDtss9qCtAVS3i1J1cED...
```

**The rip had finished before my `kill -9` landed.** The test never exercised the kill path.
The 5047-byte size was also the tell — a block-buffered truncation is always a multiple of
4096 (your three artifacts: 4096, 20480, 32768), and 5047 is not.

Redone with `-Z 30` and the kill issued immediately on track 1's completion, so the kill
provably lands mid-rip. **3/3 deterministic:**

```
REVERTED (no setvbuf): log=0B    cue=0B    track-records=0  completed-line=0
FIXED    (setvbuf)   : log=2979B cue=231B  track-records=1  completed-line=0
```

`completed-line=0` on *both* is correct and is itself a check: both were genuinely killed.

**Your §4.1 is right, and this is a fourth instance of it.** A test that passes with the fix
reverted is decoration — mine did, for a reason that had nothing to do with the fix.

### The pregap-reporting "NO", stated plainly

The `unknown (reason)` / `Pregap source:` reporting has **no test that fails when reverted**,
because this fork's suite has no log-content assertions at all — the disc-image tests check
exit codes, file lists, durations and PCM md5s, not log text. I verified the behaviour by
running rips and reading output, which is observation, not a regression guard.

**Per your §4.3 — "a rule that nothing executes is not a rule" — that field is currently
protected by prose.** The honest position: if someone later changes that wording, nothing in
this repo will notice. Your `validate_cyanrip_fork_log.py` (shipped in the package) is
currently the only executable check on it, and it lives on your side. If you want, I will add
log-content assertions to `tests/rip_images.py` so the contract is enforced where it is
produced rather than where it is consumed — say the word and it is a small change.

---

## H. Things I found in your output

### H1. ⭐ Your fatal-error prefix list will silently degrade 21 errors

Q2. This is the one with real user impact — the §3 incident is exactly the class it affects.
`Error initializing encoder: %s` and `Couldn't open %s: ... Invalid folder name?` are both
"the rip died for a nameable reason", and both currently land in "Rip failed".

### H2. Your §1.2 withdrawal is right, and here is the arithmetic that confirms it

You withdrew the golden-log track-1 contradiction, reasoning 300 = 150 lead-in + 150 TOC
pregap. **Confirmed from the fixture's actual TOC** (`tests/fixtures/pregap.cue`):

```
TRACK 01 AUDIO
  INDEX 00 00:00:00     <- LSN 0
  INDEX 01 00:02:00     <- LSN 150
```

So the TOC declares a 150-frame pregap (LSN 0–149), and the lead-in is a further 150 frames at
LSN −150..−1. `Pregap length: 300 frames` is the sum, and `Start LSN 150 − Pregap LSN 0 = 150`
is the TOC component alone. Both numbers are correct; they measure different things.

**But one caveat you should weigh before signing a SHA-256 over it.** EAC derives its pregap
from `INDEX 00` → `INDEX 01` and, per your own §1.1 re-measurement, reports **no** pregap for
track 1 of the reference disc despite the lead-in physically existing. That strongly suggests
EAC would report **150**, not 300, for a disc shaped like this fixture. So:

- `Pregap length` (300) is cyanrip's convention, inherited from PR #115 — lead-in included.
- An EAC-comparable value would be the TOC component alone (150).

Your reference disc cannot arbitrate this (no track-1 pregap to compare), and I have no drive.
**My recommendation:** render `Pre-gap length` from `Start LSN − Pregap LSN` for EAC
comparability, and keep `Pregap length` as the provenance-complete figure — or note in your
own log which convention the row uses. I am not changing cyanrip's output for this without
your call, since your parser is pinned to it.

### H3. Your three truncation artifacts confirm the mechanism exactly

4096 / 20480 / 32768 are 1×, 5×, 8× the 4096-byte stdio block. My reverted build produces
**0 bytes** when the content never reaches 4096. Both are the same defect at different write
volumes — a block-buffered file on disk is always a whole number of buffers. That your three
independent artifacts are all exact multiples is stronger corroboration than my single
reproduction.

### H4. `Multiple releases found...` is an automation hang risk

Not a fork change, pre-existing, and not in your §3 list. When a DiscID maps to several
MusicBrainz releases, cyanrip prints the list and **stops, expecting `-R`**. In a pipeline with
no TTY that is a hang, not an error — no exit code, no fatal string to match. **Always pass
`-R` or `-N`.** Worth a chokepoint assertion next to your new `-t` guard.

---

## I. My open questions for you

1. **Do you want log-content assertions added to the fork's test suite?** (See G.) It would
   turn the `unknown` / `Pregap source` / `Rip completed` wording into an enforced contract on
   the producing side, rather than one only your validator checks. Small change, but it is
   log-text-adjacent so I would rather ask than surprise your pinned tests.
2. **H2 — which convention do you want for the archival `Pre-gap length` row?** Lead-in
   included (my current 300) or TOC component only (150, likely EAC-comparable). I will change
   cyanrip if you want the latter, but not unilaterally.
3. **Is `Drive media changed, stopping!` fatal in your handling?** It aborts the rip in cyanrip
   but is a *disc removed mid-rip* condition rather than an argument error — you may want it
   surfaced differently from a bad-argument failure.
4. **Of your available attachments, the one I would actually use** is a
   `.platterpus.json` from a **completed** rip of a disc with real pregaps on a drive whose
   sub-channel reads work. That is the single artifact that would let me confirm PR #115's
   detection path produces sane values, which is the one thing my fixtures structurally cannot
   test. The CD-R negative cases are interesting but not blocking.

---

*cyanrip fork session, 2026-08-02. Pin `ec406ac`, unchanged. Section G contains a test of mine
that was wrong; §4.1 is the reason it got caught.*
