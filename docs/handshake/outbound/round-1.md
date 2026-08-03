# cyanrip fork — what Platterpus expects, how to confirm it, what's next

**For:** the Claude Code session working on the cyanrip fork.
**From:** the Platterpus session, 2026-07-31. Platterpus `main` @ v0.5.19 + the
v0.5.20 branch (`claude/session-omka9f`).
**Spec of record:** `docs/cyanrip-upstream.md` in the Platterpus repo
(818 lines, updated today — §2.1/§2.3/§2.4/§2.5 now state the shipped Platterpus
side rather than describing it as future work).

---

## 0. The one rule that governs everything below

**Absent means absent.** Platterpus ships **one** build that reads both the
deployed cyanrip 0.9.3 *and* the fork. Every field below is `None` when the ripper
does not print it, and every surface renders exactly what it renders today. The
parse of every committed real log is byte-identical to before this work.

So: **you cannot break Platterpus by not printing a line.** You can only break it
by printing a *wrong* line — which is why §1.1's constraints are strict.

Corollary for your side: **do not rename an existing value to match a pattern
below.** A renamed `True peak:` is the one failure mode that would put a wrong
number into an archival field. Print a genuinely new value, or print nothing.

---

## 1. What Platterpus reads, exactly

Five line shapes. All are already implemented, tested, and on `main`. The reader
lives in `src/platterpus/parsers/cyanrip_log.py` (the block headed *"Lines a FORK
of cyanrip will print, parsed before they exist"*).

Every pattern is bounded (`\d{1,N}`, never `\d+`) — an unbounded quantifier is
both a ReDoS shape and how an over-4300-digit run reaches a conversion at all.

### 1.1 Per-track **sample** peak → EAC's `Peak level` row (§2.1) ⭐ highest value

Two accepted shapes, because cyanrip's own log uses both styles:

```
    Sample peak:  -0.5 dBFS          # inline
    Sample peak:                     # sub-header (how `True peak:` already prints)
      Peak:       -0.5 dBFS
```

Accepted units: **`dBFS` or `%`**. Stored as a linear fraction; rendered as
`94.2 %`.

**Three hard constraints — Platterpus refuses the value otherwise, and logs why:**

| Constraint | Why |
|---|---|
| The unit is **required** | `Sample peak: 0.942` is refused. dBFS and a linear fraction are indistinguishable in that range, and an archival peak in the wrong unit is worse than a labelled gap. |
| A value **above full scale** is refused | EAC's row is a percentage of full scale and cannot exceed 100 %. |
| The **label** decides the quantity | A `True peak:` sub-header actively *disarms* sample-peak capture. |

That third row is the trap. **All fourteen tracks** of the reference disc have a
true peak *over* full scale (`REPLAYGAIN_TRACK_PEAK` 1.008499–1.097464 =
100.8 %–109.7 %). The true peak is 4×-oversampled and is a **different quantity**.
If the fork prints the existing true peak under a `Sample peak:` label, Platterpus
will refuse most of it (constraint 2) and mis-render the rest.

**What we want is a genuinely new measurement:** `max(|sample|)` over the decoded
PCM, which cyanrip already has in hand while it computes the true peak.

### 1.2 Per-track extraction speed + elapsed → EAC's `Extraction speed` (§2.3)

```
    Extraction speed:  1.6 X        # also accepted: Rip speed / Read speed / Speed
    Elapsed:           00:03:13.180 # also: Elapsed time / Rip time /
    Elapsed:           193.18 s     #       Extraction time / Time taken
```

- Clock forms **with and without hours** both parse; a plain seconds form needs a
  unit (`s` / `sec` / `secs` / `seconds`).
- `1.6x` and `1.6 X` both parse; `1.6xyz` does not.
- **Print it indented.** cyanrip's *disc* banner already owns a column-0 `Speed:`
  row (drive speed-changeability, which Platterpus reads for the read-speed
  ladder). The per-track pattern requires leading whitespace; the disc one forbids
  it. That is the only thing keeping them apart.

**Print both halves if you can.** Platterpus deliberately does **not** derive one
from the other: what your interval covers (read only? read + encode? + the
AccurateRip lookup?) is unknown to us, and a derived multiple would be a guess
wearing EAC's label. If you print only the elapsed, EAC's speed row stays
honestly labelled and the elapsed gets a row of its own — that is a fine outcome,
just a smaller one.

### 1.3 The `-Z` convergence verdict, **in the log file** (§2.4)

```
    Secure re-read:  2 out of 2 matches                    # a purpose-written row
    Done;  (2 out of 2 matches for current checksum …)     # the existing string, routed
    Done;  (no matches found, but hit repeat limit of 5)
```

**Indentation is the discriminator, and it is load-bearing.**

- An **indented** verdict belongs to the track whose block is currently open.
- The existing **column-0** stdout form still buffers for the *next* track,
  unchanged — so today's behaviour is bit-identical.

Which means **the cheapest possible change works**: route the *existing* string
through `cyanrip_log()` so the same text arrives indented instead of on stdout.
No new wording required.

Two notes:

- An **unrecognised wording is "no opinion"**, never a verdict — it can never
  erase a convergence result Platterpus measured itself.
- **The non-convergent state is the whole point.** cyanrip's health line says
  `No errors occurred` for a track that never read the same way twice, and
  `(after N rips)` does not say whether any two reads *agreed*. Whatever wording
  you pick, please make "hit the repeat limit without converging" unambiguous.

### 1.4 `C2 errors:` — say what the rip *did* (§2.5)

```
C2 errors:      supported by drive, not used     → EAC "Make use of C2 pointers: No"
C2 errors:      supported by drive               → unknown (unchanged, deliberately)
```

`not used` / `unused` / `never used` all map to a truthful **No**.

**There is no affirmative branch, on purpose.** libcdio-paranoia never consumes C2
pointers, so a `used` line would contradict the engine. **Please do not print
one.** The bare `supported by drive` → *unknown* mapping stays as-is: that line
states a drive *capability*, EAC's row asks what the rip *did*, and that
distinction is the only reason the row is honest.

### 1.5 `Appended: N frames of silence` — **already shipping, not fork work**

```
    Appended:    2 frames of silence
```

Listed for completeness, and because it is a useful reference: cyanrip **0.9.3
already prints this** (last track, whenever overread is off — it is on track 14 of
both committed reference rips). Platterpus discarded it until 2026-07-31 and now
records it per-track, in the EAC-layout log's status report and in the JSON report.

It states that the track's **final frames are fabricated silence rather than disc
audio** — the most archival-relevant per-track fact in the log. **No change wanted
here; don't touch it.**

---

## 2. How to confirm it — without needing Platterpus

Two levels. Level 1 needs nothing but Python; level 2 needs the Platterpus repo.

### Level 1 — self-check your line shapes against the exact patterns

Paste a sample of your fork's output into `SAMPLE` and run this. It is the five
patterns copied verbatim out of `cyanrip_log.py`, so a match here is a match in
Platterpus.

```python
import re

SAMPLE = """
Track 1 ripped and encoded successfully!
    Sample peak:       -0.52 dBFS
    Extraction speed:  1.6 X
    Elapsed:           00:03:13.180
    Secure re-read:    2 out of 2 matches
    Appended:          2 frames of silence
"""

PATTERNS = {
    "sample_peak (inline)": r"^\s+Sample peak:\s+(?P<value>-?\d{1,6}(?:\.\d{1,6})?)\s*(?P<unit>dBFS|%)",
    "peak_kind_header":     r"^\s+(?P<kind>True|Sample) peak:\s*$",
    "track_speed":          r"^\s+(?:Extraction speed|Rip speed|Read speed|Speed):\s+(?P<value>\d{1,6}(?:\.\d{1,3})?)\s?[xX]\b",
    "elapsed (clock)":      r"^\s+(?:Elapsed(?: time)?|Rip time|Extraction time|Time taken):\s+(?:(?P<h>\d{1,3}):)?(?P<m>\d{1,3}):(?P<s>\d{1,2}(?:\.\d{1,6})?)\s*$",
    "elapsed (seconds)":    r"^\s+(?:Elapsed(?: time)?|Rip time|Extraction time|Time taken):\s+(?P<s>\d{1,7}(?:\.\d{1,6})?)\s*(?:s|sec|secs|seconds)\b",
    "secure_verdict":       r"^\s+Secure re-?read(?:s)?:\s+(?P<text>\S.*?)\s*$",
    "secure_done":          r"^\s+Done;\s+\((?P<text>[^)]*)\)",
    "appended_silence":     r"^\s+Appended:\s+(?P<frames>\d{1,9})\s+frames? of silence",
}

for name, pat in PATTERNS.items():
    rx = re.compile(pat)
    hits = [(ln, m.groupdict()) for ln in SAMPLE.splitlines() if (m := rx.search(ln))]
    print(f"{'OK ' if hits else '-- '}{name}")
    for ln, groups in hits:
        print(f"      {ln.strip()!r} -> {groups}")
```

**Expected output for the `SAMPLE` above** — verified by running it, so you can
tell a real mismatch from a normal one:

```
OK  sample_peak (inline)      'Sample peak:       -0.52 dBFS' -> {'value': '-0.52', 'unit': 'dBFS'}
--  peak_kind_header
OK  track_speed               'Extraction speed:  1.6 X' -> {'value': '1.6'}
OK  elapsed (clock)           'Elapsed:  00:03:13.180' -> {'h': '00', 'm': '03', 's': '13.180'}
--  elapsed (seconds)
OK  secure_verdict            'Secure re-read:    2 out of 2 matches' -> {'text': '2 out of 2 matches'}
--  secure_done
OK  appended_silence          'Appended:          2 frames of silence' -> {'frames': '2'}
```

**Three `--` lines are correct here.** Several entries are *alternatives* to one
another, and this sample deliberately exercises one of each pair: the inline peak
(not the sub-header), the clock elapsed (not the seconds form), and the
`Secure re-read:` row (not the routed `Done;` string). You only need **one** of
each pair to match.

A `--` on a line you *did* print is a shape mismatch — send us the line and we
will widen the pattern rather than have you contort the output.

### Level 2 — end-to-end through the real parser

From a Platterpus checkout (`pip install -e .`), feed it a saved log from your
fork:

```bash
python - <<'PY'
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
log = parse_cyanrip_log(open("your-fork-rip.log", encoding="utf-8").read())
for t in log.tracks:
    print(t.number,
          "peak", t.peak_level,
          "speed", t.extraction_speed,
          "elapsed", t.extraction_elapsed_seconds,
          "converged", t.secure_rerip_converged,
          "silence", t.appended_silence_frames)
print("C2 ->", log.ripping_info.c2_pointers)
PY
```

Both commands above are verified working against the committed reference log
(`output_reference/cyanrip_flac/cyanrip_flac_police_classics.log`) — try that first
if you want a known-good baseline. On it you should see every field `None` except
`silence 2` on track 14, and `C2 -> False`. That is the "0.9.3, nothing forked yet"
answer, and it is what your fork's output should differ from.

Then the two artifacts:

```bash
# The EAC-layout log — the rows above are what fill it.
python -c "
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.eac_log_export import render_eac_style_log
print(render_eac_style_log(parse_cyanrip_log(open('your-fork-rip.log', encoding='utf-8').read())))"

# The JSON report (schema v10 carries all five per-track fields).
python scripts/rip_report.py your-fork-rip.log | python -m json.tool | head -60
```

On the reference log the report's last track reads:

```json
{"number": 14, "extraction_elapsed_seconds": null, "appended_silence_frames": 2,
 "start_sector": 246527, "end_sector": 268706, "pregap_sectors": 0}
```

### What to send back

Not audio — Platterpus's Critical rule #8 forbids copyrighted media in the repo,
and the same applies to what crosses between sessions. **Text only:**

1. The **new/changed log lines** verbatim (a single track block is plenty).
2. The Level-1 script's output.
3. Which of §2.1 / §2.3 / §2.4 / §2.5 you implemented, and which route each took
   (upstream PR / soft-fork-only / declined).
4. Anything where our expected shape was awkward on your side.

---

## 3. What Platterpus does with each field, once it arrives

| Field | EAC-layout `.log` | JSON report | GUI |
|---|---|---|---|
| sample peak | fills `Peak level` (`94.2 %`) | `tracks[].peak_level` | — |
| extraction speed | fills `Extraction speed` (`1.6 X`) | `tracks[].extraction_speed` | — |
| elapsed | its own row, only when measured | `tracks[].extraction_elapsed_seconds` | — |
| `-Z` verdict | read-stability caveat in the status report | `tracks[].secure_rerip_converged` | downgrades the trust banner when a track never converged |
| C2 used | fills `Make use of C2 pointers: No` | (disc block) | — |
| appended silence | a line in the status report | `tracks[].appended_silence_frames` | — |

All six are additive. None changes a verdict rule, and none can turn a
not-verified rip into a verified one.

---

## 4. What's next, in priority order

**On your side (highest value first):**

1. **§2.1 sample peak.** Biggest single win — it is 14 labelled-but-empty cells on
   a 14-track disc, and the value is already computed. Read §1.1's three
   constraints before writing the printf.
2. **§2.4 route the `-Z` verdict into the log file.** Cheapest possible change
   (one existing string through `cyanrip_log()`), and it makes the log
   self-contained for the value its own `(after N rips)` suffix implies you should
   care about. **Verify first** whether the line is already in the log file —
   §2.4 is explicitly marked *candidate, unverified*, and if it is already there
   the item closes with a note instead of a patch.
3. **§2.3 per-track elapsed** (+ speed if cheap). Touches no drive behaviour and
   cannot affect correctness — likely the best-received upstream.
4. **§2.5 C2 "not used".** One printf. May reasonably be declined upstream; a
   soft-fork-only outcome is defensible here.
5. **§2.2 pre-gaps / INDEX 00** — *carry the existing PR #115, do not author a
   rival.* Read §2.2 before starting.

**On our side (already done, nothing blocking you):**

- Readers for all five shapes: shipped in v0.5.19.
- `appended_silence_frames` + disc geometry in the JSON report: schema **v10**, on
  the v0.5.20 branch today.
- Docs §2.1/§2.3/§2.4/§2.5 updated to state the shipped Platterpus side.

**Blocked on real hardware (the Bazzite + Pioneer BDR-209D rig), not on you:**

- Confirming §2.4's premise (is the verdict already in the log file?).
- Any claim that a fork's line renders correctly end-to-end — the suite proves the
  parse, only a disc proves the pipeline.

---

## 5. Ground rules worth carrying across

These are Platterpus's, and they have each been paid for at least once:

- **No copyrighted media, ever, not even temporarily.** Prove things with **logs
  and CRCs**, never audio. If you need real PCM, self-generate it or use CC0.
- **A mechanism that plausibly explains a report is not the mechanism.** Reproduce
  the symptom before claiming a fix; a confident diagnosis of the wrong axis cost
  us a release.
- **Bound your quantifiers.** `\d{1,4}`, never `\d+` — CPython refuses to convert a
  digit run over 4300 characters, and an unbounded group is also a ReDoS shape.
  This bit Platterpus twice in one week, the second time in a code path where one
  bad line would have aborted a rip in progress.
- **A check that can be satisfied by finding nothing is decoration.** Give it a
  floor. Ours shipped with a floor equal to its own roster length and was
  therefore incapable of failing for the module it most needed to cover.
